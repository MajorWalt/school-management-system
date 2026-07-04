from django.db import models
from core.models import School
from accounts.models import User


class Attendance(models.Model):
    STATUS_CHOICES = [
        ("present", "Present"),
        ("absent", "Absent"),
        ("late", "Late"),
        ("excused", "Excused"),
    ]

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="attendance_records")
    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="attendance_records")
    homeroom = models.ForeignKey("scheduling.Homeroom", on_delete=models.CASCADE, related_name="attendance_records", null=True, blank=True)
    section = models.ForeignKey("scheduling.Section", on_delete=models.SET_NULL, null=True, blank=True, related_name="attendance_records")
    date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="present")
    note = models.TextField(blank=True)
    marked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="attendance_marked")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "attendance"
        unique_together = ("student", "homeroom", "date")
        ordering = ["-date"]

    def __str__(self):
        return f"{self.student} — {self.date} — {self.status}"
