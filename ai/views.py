import datetime

from django.conf import settings as django_settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from accounts.utils import is_admin
from core.activity import log_activity
from core.decorators import admin_or_teacher_required, admin_required, tenant_required
from grades.models import GradeComment
from grades.utils import grade_window_is_open
from grades.views import get_hod_departments, get_teacher_staff, section_in_departments
from scheduling.models import Section

from .ask import ask
from .ask_tools import AskScope
from .client import AIError, is_ai_enabled
from .comments import section_students
from .models import AIUsageLog, AskAIQuestion, CommentBatch, CommentDraft, SchoolAISettings
from .tasks import ai_test_request, generate_section_comments

ASK_SESSION_KEY = "ask_ai_history"
ASK_MAX_TURNS = 10
ASK_QUESTION_MAX_CHARS = 500


@login_required
@tenant_required
@admin_required
@require_http_methods(["GET", "POST"])
def settings_view(request):
    """AI Settings page for admins."""
    school = request.school
    ai_settings = SchoolAISettings.for_school(school)

    if request.method == "POST":
        enabled = request.POST.get("enabled") == "on"

        with transaction.atomic():
            ai_settings.enabled = enabled
            ai_settings.updated_by = request.user
            ai_settings.save()
            pass

        log_activity(
            request,
            "other",
            f"{'Enabled' if enabled else 'Disabled'} AI features",
        )

        messages.success(
            request,
            f"AI features {'enabled' if enabled else 'disabled'} successfully.",
        )
        return redirect("ai:settings")
        pass

    # Get this month's usage stats
    now = datetime.datetime.now()
    month_start = datetime.date(now.year, now.month, 1)

    usage_stats_raw = (
        AIUsageLog.objects.filter(school=school, created_at__gte=month_start)
        .values("feature")
        .annotate(
            total_requests=Count("id"),
            total_input_tokens=Sum("input_tokens"),
            total_output_tokens=Sum("output_tokens"),
        )
        .order_by("feature")
    )

    # Format feature names for display
    usage_stats = []
    for stat in usage_stats_raw:
        stat["feature_display"] = stat["feature"].replace("_", " ").title()
        usage_stats.append(stat)
        pass

    # Get overall month stats
    overall_stats = AIUsageLog.objects.filter(school=school, created_at__gte=month_start).aggregate(
        total_requests=Count("id"),
        total_input_tokens=Sum("input_tokens"),
        total_output_tokens=Sum("output_tokens"),
    )

    # Get recent logs
    recent_logs = AIUsageLog.objects.filter(school=school).select_related("user").order_by("-created_at")[:25]

    # Check if API key is configured
    api_key_configured = bool(django_settings.ANTHROPIC_API_KEY)

    context = {
        "ai_settings": ai_settings,
        "api_key_configured": api_key_configured,
        "current_model": django_settings.AI_MODEL,
        "usage_stats": usage_stats,
        "overall_stats": overall_stats,
        "recent_logs": recent_logs,
        "month_name": now.strftime("%B %Y"),
    }

    return render(request, "ai/settings.html", context)
    pass


@login_required
@tenant_required
@admin_required
@require_http_methods(["POST"])
def test_view(request):
    """Send a test AI request."""
    school = request.school

    if not is_ai_enabled(school):
        messages.error(request, "AI is disabled for your school. Please enable it first.")
        return redirect("ai:settings")
        pass

    # Queue the test request
    ai_test_request.delay(school.pk, request.user.pk)

    log_activity(request, "other", "Sent AI test request")

    messages.info(request, "Test request sent. Refresh the page to see the result in the usage log.")

    return redirect("ai:settings")
    pass


# -- AI report card comments ---------------------------------------------------


def _get_section(request, section_pk):
    return get_object_or_404(
        Section.objects.select_related("course", "form", "academic_year", "teacher"),
        pk=section_pk,
        school=request.school,
    )
    pass


def _comment_access(request, section):
    """
    (can_view, can_edit, window_open).
    View: admin, section teacher, HOD of the course's department.
    Edit (draft/approve): admin, or section teacher while the grade window is open.
    """
    school = request.school
    admin = is_admin(request.user, school)
    staff = get_teacher_staff(request.user)
    is_owner = bool(staff and section.teacher_id == staff.pk)
    hod_can_view = section_in_departments(section, get_hod_departments(staff))
    window_open = grade_window_is_open(school, section.academic_year, section.term_number, section.form)
    can_view = admin or is_owner or hod_can_view
    can_edit = admin or (is_owner and window_open)
    return can_view, can_edit, window_open
    pass


@login_required
@tenant_required
def comment_review(request, section_pk):
    section = _get_section(request, section_pk)
    can_view, can_edit, window_open = _comment_access(request, section)
    if not can_view:
        messages.error(request, "Access denied.")
        return redirect("grades:home")

    school = request.school
    students = section_students(section)
    drafts = {d.student_id: d for d in CommentDraft.objects.filter(school=school, section=section)}
    current = {c.student_id: c.comment for c in GradeComment.objects.filter(school=school, section=section)}

    rows = [
        {
            "student": s,
            "draft": drafts.get(s.pk),
            "current_comment": current.get(s.pk, ""),
        }
        for s in students
    ]
    pending_count = sum(1 for r in rows if r["draft"] and r["draft"].status == "pending")
    batch = CommentBatch.objects.filter(school=school, section=section).first()

    return render(
        request,
        "ai/comment_review.html",
        {
            "section": section,
            "rows": rows,
            "batch": batch,
            "pending_count": pending_count,
            "can_edit": can_edit,
            "window_open": window_open,
            "ai_enabled": is_ai_enabled(school),
        },
    )
    pass


@login_required
@tenant_required
@require_http_methods(["POST"])
def comment_generate(request, section_pk):
    section = _get_section(request, section_pk)
    _, can_edit, _ = _comment_access(request, section)
    if not can_edit:
        messages.error(request, "You can't draft comments for this section.")
        return redirect("ai:comment_review", section_pk=section.pk)

    school = request.school
    if not is_ai_enabled(school):
        messages.error(request, "AI features are disabled for this school.")
        return redirect("ai:comment_review", section_pk=section.pk)

    latest = CommentBatch.objects.filter(school=school, section=section).first()
    if latest and latest.is_active:
        messages.info(request, "Comments are already being drafted for this section.")
        return redirect("ai:comment_review", section_pk=section.pk)

    with transaction.atomic():
        batch = CommentBatch.objects.create(school=school, section=section, requested_by=request.user)
        transaction.on_commit(lambda: generate_section_comments.delay(batch.pk))

    log_activity(request, "other", f"Requested AI comment drafts for {section}.")
    messages.info(request, "Drafting comments. This page updates as they come in.")
    return redirect("ai:comment_review", section_pk=section.pk)
    pass


@login_required
@tenant_required
def comment_progress(request, section_pk):
    """HTMX poll target. Returns the progress partial, or HX-Refresh once the batch is finished."""
    section = _get_section(request, section_pk)
    can_view, _, _ = _comment_access(request, section)
    if not can_view:
        return HttpResponse(status=403)

    batch = CommentBatch.objects.filter(school=request.school, section=section).first()
    if not batch or not batch.is_active:
        response = HttpResponse("")
        response["HX-Refresh"] = "true"
        return response

    return render(request, "ai/_comment_progress.html", {"section": section, "batch": batch})
    pass


def _approve(request, section, draft):
    """Copy draft text (as edited on the page) into GradeComment. Returns True if approved."""
    text = request.POST.get(f"text_{draft.pk}", draft.draft_text).strip()
    if not text:
        return False
    GradeComment.objects.update_or_create(
        section=section,
        student=draft.student,
        defaults={
            "school": request.school,
            "comment": text,
            "entered_by": request.user,
        },
    )
    draft.draft_text = text
    draft.status = "approved"
    draft.reviewed_by = request.user
    draft.reviewed_at = timezone.now()
    draft.save(update_fields=["draft_text", "status", "reviewed_by", "reviewed_at", "updated_at"])
    return True
    pass


@login_required
@tenant_required
@require_http_methods(["POST"])
def comment_review_action(request, section_pk):
    """
    action = "approve_all" | "approve:<draft_id>" | "discard:<draft_id>"
    Edited text comes from text_<draft_id> fields.
    """
    section = _get_section(request, section_pk)
    _, can_edit, _ = _comment_access(request, section)
    if not can_edit:
        messages.error(request, "You can't approve comments for this section.")
        return redirect("ai:comment_review", section_pk=section.pk)

    action = request.POST.get("action", "")
    drafts = list(CommentDraft.objects.filter(school=request.school, section=section).select_related("student"))

    if action == "approve_all":
        targets = [d for d in drafts if d.status == "pending"]
        approved = 0
        skipped = 0
        with transaction.atomic():
            for draft in targets:
                if _approve(request, section, draft):
                    approved += 1
                else:
                    skipped += 1
        log_activity(request, "other", f"Approved {approved} AI comment drafts for {section}.")
        msg = f"{approved} comment(s) approved."
        if skipped:
            msg += f" {skipped} skipped (empty text)."
        messages.success(request, msg)
        return redirect("ai:comment_review", section_pk=section.pk)

    verb, _, raw_id = action.partition(":")
    try:
        draft_id = int(raw_id)
    except ValueError:
        messages.error(request, "Unknown action.")
        return redirect("ai:comment_review", section_pk=section.pk)

    draft = next((d for d in drafts if d.pk == draft_id), None)
    if draft is None:
        messages.error(request, "Draft not found.")
        return redirect("ai:comment_review", section_pk=section.pk)

    if verb == "discard":
        draft.status = "discarded"
        draft.reviewed_by = request.user
        draft.reviewed_at = timezone.now()
        draft.save(update_fields=["status", "reviewed_by", "reviewed_at", "updated_at"])
        log_activity(request, "other", f"Discarded AI comment draft for {draft.student} in {section}.")
        messages.info(request, f"Draft discarded for {draft.student.get_full_name()}.")
        return redirect("ai:comment_review", section_pk=section.pk)

    if verb == "approve":
        with transaction.atomic():
            ok = _approve(request, section, draft)
        if ok:
            log_activity(request, "other", f"Approved AI comment for {draft.student} in {section}.")
            messages.success(request, f"Comment approved for {draft.student.get_full_name()}.")
        else:
            messages.error(request, "Comment text is empty.")
        return redirect("ai:comment_review", section_pk=section.pk)

    messages.error(request, "Unknown action.")
    return redirect("ai:comment_review", section_pk=section.pk)
    pass


# -- Ask AI --------------------------------------------------------------------


def _get_history(request):
    data = request.session.get(ASK_SESSION_KEY) or {}
    return data.get(str(request.school.pk), [])
    pass


def _save_history(request, history):
    data = request.session.get(ASK_SESSION_KEY) or {}
    data[str(request.school.pk)] = history[-ASK_MAX_TURNS * 2 :]
    request.session[ASK_SESSION_KEY] = data
    pass


def _ask_limit_message(school, user):
    """User-facing message if a rate limit is reached, else None."""
    now = timezone.now()
    day_start = timezone.localtime(now).replace(hour=0, minute=0, second=0, microsecond=0)
    daily_limit = getattr(django_settings, "AI_ASK_DAILY_LIMIT", 200)
    hourly_limit = getattr(django_settings, "AI_ASK_HOURLY_LIMIT", 30)

    if AskAIQuestion.objects.filter(school=school, created_at__gte=day_start).count() >= daily_limit:
        return "The school has reached today's question limit. Please try again tomorrow."
    if AskAIQuestion.objects.filter(school=school, user=user, created_at__gte=now - datetime.timedelta(hours=1)).count() >= hourly_limit:
        return "You've reached the hourly question limit. Please try again later."
    return None
    pass


def _assistant_reply(request, text):
    return render(request, "ai/_ask_messages.html", {"chat_messages": [{"role": "assistant", "content": text}]})
    pass


@admin_or_teacher_required
@tenant_required
@require_http_methods(["GET"])
def ask_history(request):
    history = _get_history(request)
    return render(request, "ai/_ask_messages.html", {"chat_messages": history, "show_intro": not history})
    pass


@admin_or_teacher_required
@tenant_required
@require_http_methods(["POST"])
def ask_send(request):
    school = request.school
    question = (request.POST.get("question") or "").strip()[:ASK_QUESTION_MAX_CHARS]
    if not question:
        return HttpResponse("")

    if not is_ai_enabled(school):
        return _assistant_reply(request, "AI features are turned off for this school.")

    limit_message = _ask_limit_message(school, request.user)
    if limit_message:
        return _assistant_reply(request, limit_message)

    history = _get_history(request)
    scope = AskScope(request.user, school)
    succeeded = True
    try:
        answer, calls = ask(scope, history, question)
    except AIError:
        answer = "Sorry, the assistant is unavailable right now. Please try again shortly."
        calls = 0
        succeeded = False

    AskAIQuestion.objects.create(school=school, user=request.user, api_calls=calls, succeeded=succeeded)

    if succeeded:
        _save_history(request, history + [{"role": "user", "content": question}, {"role": "assistant", "content": answer}])

    return _assistant_reply(request, answer)
    pass


@admin_or_teacher_required
@tenant_required
@require_http_methods(["POST"])
def ask_reset(request):
    _save_history(request, [])
    return render(request, "ai/_ask_messages.html", {"chat_messages": [], "show_intro": True})
    pass