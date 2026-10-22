from django.db import models
from core.models import School


class AtRiskScore(models.Model):

    BAND_CHOICES = [
        ("low", "Low"),
        ("watch", "Watch"),
        ("high", "High"),
    ]

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="risk_scores")
    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="risk_scores")
    academic_year = models.ForeignKey("scheduling.AcademicYear", on_delete=models.CASCADE, related_name="risk_scores")
    term_number = models.PositiveIntegerField()
    computed_on = models.DateField()
    score = models.DecimalField(max_digits=4, decimal_places=1)
    band = models.CharField(max_length=10, choices=BAND_CHOICES)
    model_version = models.CharField(max_length=20, default="rules-v1")
    feature_snapshot = models.JSONField(default=dict)
    explanation = models.TextField(blank=True)  
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "at_risk_scores"
        unique_together = ("student", "computed_on")
        ordering = ["-computed_on", "-score"]
        indexes = [models.Index(fields=["school", "computed_on", "band"])]

    def __str__(self):
        return f"{self.student} - {self.computed_on} - {self.score} ({self.band})"

    @property
    def top_factors(self):
        return (self.feature_snapshot or {}).get("top_factors", [])