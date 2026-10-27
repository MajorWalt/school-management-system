from celery import shared_task
from django.db.models import F
from django.utils import timezone

from accounts.models import User
from core.models import School

from .client import AIDisabled, AIError, call_claude, response_text
from .comments import COMMENT_MAX_TOKENS, SYSTEM_PROMPT, build_comment_inputs, build_user_message
from .models import CommentBatch, CommentDraft

# Attempts per student when the reply has no usable text.
EMPTY_REPLY_ATTEMPTS = 2


@shared_task
def ai_test_request(school_id, user_id):
    """Test AI request for a school."""
    try:
        school = School.objects.get(pk=school_id)
        user = User.objects.get(pk=user_id)

        call_claude(
            school=school,
            user=user,
            feature="test",
            messages=[{"role": "user", "content": "Reply with the single word: ok"}],
            max_tokens=10,
        )
        pass
    except AIError:
        # Already logged by call_claude
        pass
    except Exception:
        # Unexpected errors - could log separately if needed
        pass
    pass


def _save_draft(batch, student, text, status, error=""):
    CommentDraft.objects.update_or_create(
        section=batch.section,
        student=student,
        defaults={
            "school": batch.school,
            "batch": batch,
            "draft_text": text,
            "status": status,
            "error_message": error,
            "reviewed_by": None,
            "reviewed_at": None,
        },
    )
    pass


def _bump(batch, failed=False):
    """Atomic progress counter update so polling sees live progress."""
    updates = {"completed": F("completed") + 1}
    if failed:
        updates["failed"] = F("failed") + 1
    CommentBatch.objects.filter(pk=batch.pk).update(**updates)
    pass


def _draft_comment(school, user, section, row):
    """
    (text, stop_reason). Retries when the reply has no text or was cut off at max_tokens,
    so a truncated comment is never saved as a draft.
    """
    stop_reason = None
    for _ in range(EMPTY_REPLY_ATTEMPTS):
        response = call_claude(
            school=school,
            user=user,
            feature="report_comment",
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": build_user_message(section, row)}],
            max_tokens=COMMENT_MAX_TOKENS,
        )
        stop_reason = getattr(response, "stop_reason", None)
        text = response_text(response).strip().strip('"').strip()
        if text and stop_reason != "max_tokens":
            return text, stop_reason
    return "", stop_reason
    pass


@shared_task
def generate_section_comments(batch_id):
    """Draft one AI comment per enrolled student in the batch's section."""
    try:
        batch = CommentBatch.objects.select_related("school", "section__course", "section__form", "requested_by").get(pk=batch_id)
    except CommentBatch.DoesNotExist:
        return
        pass

    school = batch.school
    section = batch.section
    user = batch.requested_by

    try:
        rows = build_comment_inputs(school, section)
        batch.status = "running"
        batch.total = len(rows)
        batch.save(update_fields=["status", "total"])

        for row in rows:
            student = row["student"]

            if row["term_grade"] is None:
                _save_draft(batch, student, "", "error", "No grades recorded for this term.")
                _bump(batch, failed=True)
                continue

            try:
                text, stop_reason = _draft_comment(school, user, section, row)
                if text:
                    _save_draft(batch, student, text, "pending")
                    _bump(batch)
                else:
                    _save_draft(batch, student, "", "error", f"Empty or cut-off response from AI (stop_reason: {stop_reason}).")
                    _bump(batch, failed=True)
            except AIDisabled:
                raise
            except AIError as e:
                _save_draft(batch, student, "", "error", str(e)[:500])
                _bump(batch, failed=True)

        batch.status = "done"
    except AIDisabled:
        batch.status = "failed"
        batch.error_message = "AI was disabled for this school during the run."
    except Exception as e:
        batch.status = "failed"
        batch.error_message = f"{type(e).__name__}: {e}"[:1000]

    batch.finished_at = timezone.now()
    batch.save(update_fields=["status", "error_message", "finished_at"])
    pass