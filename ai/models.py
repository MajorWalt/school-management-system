from django.db import models
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
        ("ask_edara", "Ask Edara"),
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
