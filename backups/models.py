from django.db import models
from core.models import School
from accounts.models import User


class BackupLog(models.Model):
    STATUS_CHOICES = [
        ("success", "Success"),
        ("failed", "Failed"),
    ]

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="backup_logs")
    triggered_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="backups_triggered")
    filename = models.CharField(max_length=255, blank=True)
    file_size_bytes = models.BigIntegerField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="success")
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "backup_logs"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.school} — {self.filename} — {self.status}"

    @property
    def file_size_display(self):
        if not self.file_size_bytes:
            return "—"
        kb = self.file_size_bytes / 1024
        if kb < 1024:
            return f"{kb:.1f} KB"
        return f"{kb / 1024:.1f} MB"
