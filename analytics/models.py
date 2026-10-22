from django.db import models
from core.models import School


class AtRiskScore(models.Model):
    """
    One row per student per day. score 0-100, higher = more at risk.
    feature_snapshot holds every input, form mean, z-score and contribution used,
    so any score can be explained, audited, or used later as ML training data.
    """

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
    explanation = models.TextField(blank=True)  # filled later by the AI at-risk explanation feature
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


class PromotionCriteria(models.Model):
    """
    What a student in one form must achieve by year end to move up (or, in the final form, to graduate).
    Admin-managed. Pass/fail is judged on year averages built from the shared weighted term grades.
    """

    OUTCOME_CHOICES = [
        ("promotion", "Promotion to next form"),
        ("graduation", "Graduation"),
    ]

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="promotion_criteria")
    form = models.ForeignKey("scheduling.Form", on_delete=models.CASCADE, related_name="promotion_criteria")
    outcome = models.CharField(max_length=20, choices=OUTCOME_CHOICES, default="promotion")
    pass_mark = models.PositiveIntegerField(default=55, help_text="Year average needed to pass a subject (%).")
    min_overall_average = models.DecimalField(
        max_digits=4, decimal_places=1, null=True, blank=True, help_text="Optional. Minimum overall year average (%)."
    )
    max_failed_subjects = models.PositiveIntegerField(null=True, blank=True, help_text="Optional. Most subjects a student may fail.")
    notes = models.TextField(blank=True)
    active = models.BooleanField(default=True)
    updated_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "promotion_criteria"
        unique_together = ("school", "form")
        ordering = ["form__order", "form__name"]

    def __str__(self):
        return f"{self.form} - {self.get_outcome_display()}"


class CriteriaRequirement(models.Model):
    """
    One rule inside a form's criteria: pass at least `min_to_pass` of the listed subject areas.
    e.g. "Mathematics" = [mathematics], 1 ; "Foreign language" = [french, spanish], 1 ;
         "Religion or History" = [religion, caribbean_history], 1
    """

    criteria = models.ForeignKey(PromotionCriteria, on_delete=models.CASCADE, related_name="requirements")
    label = models.CharField(max_length=100)
    subject_areas = models.JSONField(default=list)  # values from Course.SUBJECT_AREA_CHOICES
    min_to_pass = models.PositiveIntegerField(default=1)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "criteria_requirements"
        ordering = ["order", "pk"]

    def __str__(self):
        return f"{self.criteria.form} - {self.label}"