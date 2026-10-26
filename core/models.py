from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class School(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "schools"

    def __str__(self):
        return self.name


class ActivityLog(models.Model):
    ACTION_CHOICES = [
        # Auth
        ("login", "Logged In"),
        ("logout", "Logged Out"),
        # Students
        ("student_add", "Added Student"),
        ("student_edit", "Edited Student"),
        ("student_status", "Changed Student Status"),
        ("student_bulk_enrol", "Bulk Enrolled Students"),
        # Staff
        ("staff_add", "Added Staff Member"),
        ("staff_edit", "Edited Staff Member"),
        ("staff_deactivate", "Deactivated Staff Member"),
        ("staff_reactivate", "Reactivated Staff Member"),
        # Attendance
        ("attendance_marked", "Marked Attendance"),
        # Grades
        ("grades_saved", "Saved Grades"),
        ("evaluation_created", "Created Evaluation"),
        ("evaluation_edited", "Edited Evaluation"),
        ("evaluation_deleted", "Deleted Evaluation"),
        ("grade_window_updated", "Updated Grade Window"),
        # Report cards
        ("report_card_generated", "Generated Report Cards"),
        ("report_card_published", "Published Report Card"),
        # Merits
        ("merit_awarded", "Awarded Merit"),
        ("demerit_issued", "Issued Demerit"),
        ("merit_deleted", "Deleted Merit"),
        ("demerit_deleted", "Deleted Demerit"),
        # Behaviour
        ("behaviour_incident_created", "Created Behaviour Incident"),
        ("behaviour_incident_updated", "Updated Behaviour Incident"),
        ("behaviour_incident_deleted", "Deleted Behaviour Incident"),
        # Backup
        ("backup_run", "Ran Database Backup"),
        # Scheduling
        ("section_created", "Created Section"),
        ("enrolment_added", "Enrolled Student in Section"),
        # Other
        ("other", "Other Action"),
    ]

    school = models.ForeignKey("core.School", on_delete=models.CASCADE, related_name="activity_logs")
    user = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, related_name="activity_logs")
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "activity_logs"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} - {self.get_action_display()} - {self.created_at:%Y-%m-%d %H:%M}"


class SchoolSettings(models.Model):
    """Admin-configurable settings for academic and behavioral thresholds."""

    school = models.OneToOneField("core.School", on_delete=models.CASCADE, related_name="settings")

    # High Priority - Core Academic Settings
    pass_mark = models.PositiveIntegerField(
        default=55, validators=[MinValueValidator(0), MaxValueValidator(100)], help_text="Pass/fail threshold for all subjects (0-100)"
    )
    honours_1st_class = models.PositiveIntegerField(
        default=85, validators=[MinValueValidator(0), MaxValueValidator(100)], help_text="1st Class Honours threshold (0-100)"
    )
    honours_2nd_class = models.PositiveIntegerField(
        default=75, validators=[MinValueValidator(0), MaxValueValidator(100)], help_text="2nd Class Honours threshold (0-100)"
    )
    failing_override = models.PositiveIntegerField(
        default=3, validators=[MinValueValidator(1), MaxValueValidator(20)], help_text="Auto-flag 'High risk' if this many subjects failed"
    )
    high_threshold = models.PositiveIntegerField(
        default=70, validators=[MinValueValidator(0), MaxValueValidator(100)], help_text="At-risk score for 'High risk' band (0-100)"
    )
    watch_threshold = models.PositiveIntegerField(
        default=60, validators=[MinValueValidator(0), MaxValueValidator(100)], help_text="At-risk score for 'Watch' risk band (0-100)"
    )

    # Medium Priority - Academic Configuration
    coursework_weight = models.PositiveIntegerField(
        default=60, validators=[MinValueValidator(0), MaxValueValidator(100)], help_text="Weight of coursework in final grade (%)"
    )
    exam_weight = models.PositiveIntegerField(
        default=40, validators=[MinValueValidator(0), MaxValueValidator(100)], help_text="Weight of exam in final grade (%)"
    )
    min_peers = models.PositiveIntegerField(
        default=5, validators=[MinValueValidator(1), MaxValueValidator(50)], help_text="Minimum students per form for statistical reliability"
    )
    min_merits = models.PositiveIntegerField(default=10, validators=[MinValueValidator(1), MaxValueValidator(100)], help_text="Threshold for top merits list")
    min_demerits = models.PositiveIntegerField(
        default=5, validators=[MinValueValidator(1), MaxValueValidator(100)], help_text="Threshold for top demerits list"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "school_settings"
        verbose_name = "School Settings"
        verbose_name_plural = "School Settings"

    def __str__(self):
        return f"Settings for {self.school.name}"

    def clean(self):
        """Validate that weights sum to 100."""
        if self.coursework_weight + self.exam_weight != 100:
            raise ValueError("Coursework and Exam weights must sum to 100")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
