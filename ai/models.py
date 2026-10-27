import datetime

from django.db import models
from django.utils import timezone

from core.models import School


class SchoolAISettings(models.Model):
    """Per-school toggle for AI features."""

    school = models.OneToOneField(School, on_delete=models.CASCADE, related_name="ai_settings")
    enabled = models.BooleanField(default=False)
    updated_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="ai_settings_updates")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "school_ai_settings"
        verbose_name = "School AI Settings"
        verbose_name_plural = "School AI Settings"

    def __str__(self):
        return f"AI Settings for {self.school.name} ({'enabled' if self.enabled else 'disabled'})"
        pass

    @classmethod
    def for_school(cls, school):
        """Get or create settings for a school."""
        settings, _ = cls.objects.get_or_create(school=school)
        return settings
        pass


class AIUsageLog(models.Model):
    """Log every AI API request for usage tracking and billing."""

    FEATURE_CHOICES = [
        ("report_comment", "Report Comment"),
        ("ask_ai", "Ask AI"),
        ("risk_explanation", "Risk Explanation"),
        ("test", "Test"),
    ]

    STATUS_CHOICES = [
        ("success", "Success"),
        ("error", "Error"),
        ("blocked", "Blocked"),
    ]

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="ai_usage_logs")
    user = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="ai_usage_logs")
    feature = models.CharField(max_length=20, choices=FEATURE_CHOICES)
    model = models.CharField(max_length=50)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    cache_read_tokens = models.PositiveIntegerField(default=0)
    cache_creation_tokens = models.PositiveIntegerField(default=0)
    latency_ms = models.PositiveIntegerField(default=0)
    request_id = models.CharField(max_length=100, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "ai_usage_logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["school", "created_at"]),
        ]

    def __str__(self):
        return f"{self.school.name} - {self.feature} - {self.status} - {self.created_at:%Y-%m-%d %H:%M}"
        pass


class CommentBatch(models.Model):
    """One AI comment-drafting run for one section."""

    STATUS_CHOICES = [
        ("queued", "Queued"),
        ("running", "Running"),
        ("done", "Done"),
        ("failed", "Failed"),
    ]

    # A queued/running batch older than this is treated as dead (e.g. worker crashed).
    STALE_AFTER = datetime.timedelta(minutes=30)

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="ai_comment_batches")
    section = models.ForeignKey("scheduling.Section", on_delete=models.CASCADE, related_name="ai_comment_batches")
    requested_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="ai_comment_batches")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="queued")
    total = models.PositiveIntegerField(default=0)
    completed = models.PositiveIntegerField(default=0)
    failed = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "ai_comment_batches"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.section} - {self.status} ({self.completed}/{self.total})"
        pass

    @property
    def is_active(self):
        if self.status not in ("queued", "running"):
            return False
        return timezone.now() - self.created_at < self.STALE_AFTER
        pass

    @property
    def progress_pct(self):
        if not self.total:
            return 0
        return int(self.completed * 100 / self.total)
        pass


class CommentDraft(models.Model):
    """
    AI-drafted subject comment for one student in one section.
    Never shown on a report card. Approving copies the text into grades.GradeComment.
    """

    STATUS_CHOICES = [
        ("pending", "Pending review"),
        ("approved", "Approved"),
        ("discarded", "Discarded"),
        ("error", "Error"),
    ]

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="ai_comment_drafts")
    section = models.ForeignKey("scheduling.Section", on_delete=models.CASCADE, related_name="ai_comment_drafts")
    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="ai_comment_drafts")
    batch = models.ForeignKey(CommentBatch, on_delete=models.SET_NULL, null=True, blank=True, related_name="drafts")
    draft_text = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    error_message = models.TextField(blank=True)
    reviewed_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="ai_comment_drafts_reviewed")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_comment_drafts"
        unique_together = ("section", "student")
        ordering = ["student__last_name", "student__first_name"]

    def __str__(self):
        return f"{self.student} - {self.section} - {self.status}"
        pass


class AskAIQuestion(models.Model):
    """One Ask AI question. Metadata only - question and answer text are never stored. Used for rate limits."""

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="ask_ai_questions")
    user = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="ask_ai_questions")
    api_calls = models.PositiveSmallIntegerField(default=0)
    succeeded = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "ask_ai_questions"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["school", "created_at"]),
        ]

    def __str__(self):
        return f"{self.school.name} - {self.user} - {self.created_at:%Y-%m-%d %H:%M}"
        pass