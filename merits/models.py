from django.db import models
from core.models import School


class MeritRecord(models.Model):
    CATEGORY_CHOICES = [
        ("academic", "Academic"),
        ("behaviour", "Behaviour"),
        ("sports", "Sports"),
        ("arts", "Arts"),
        ("community", "Community Service"),
        ("leadership", "Leadership"),
        ("other", "Other"),
    ]

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="merit_records")
    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="merit_records")
    awarded_by = models.ForeignKey("staff.Staff", on_delete=models.SET_NULL, null=True, related_name="merits_awarded")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    reason = models.TextField()
    count = models.PositiveIntegerField(default=1)
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "merit_records"
        ordering = ["-date"]

    def __str__(self):
        return f"{self.student} — Merit — {self.count} — {self.date}"


class DemeritRecord(models.Model):
    CATEGORY_CHOICES = [
        ("misconduct", "Misconduct"),
        ("tardiness", "Tardiness"),
        ("uniform", "Uniform Violation"),
        ("disrespect", "Disrespect"),
        ("dishonesty", "Dishonesty"),
        ("other", "Other"),
    ]

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="demerit_records")
    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="demerit_records")
    awarded_by = models.ForeignKey("staff.Staff", on_delete=models.SET_NULL, null=True, related_name="demerits_awarded")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    reason = models.TextField()
    count = models.PositiveIntegerField(default=1)
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "demerit_records"
        ordering = ["-date"]

    def __str__(self):
        return f"{self.student} — Demerit — {self.count} — {self.date}"
