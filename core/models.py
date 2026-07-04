from django.db import models


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
        return f"{self.user} — {self.get_action_display()} — {self.created_at:%Y-%m-%d %H:%M}"
