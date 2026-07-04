from django.db import models
from django.core.exceptions import ValidationError
from core.models import School
from accounts.models import User


class GradeWindow(models.Model):
    """Controls whether teachers can enter grades for a form/term."""

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="grade_windows")
    academic_year = models.ForeignKey("scheduling.AcademicYear", on_delete=models.CASCADE, related_name="grade_windows")
    term_number = models.PositiveIntegerField()
    form = models.ForeignKey("scheduling.Form", on_delete=models.CASCADE, related_name="grade_windows")
    is_open = models.BooleanField(default=False)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="grade_windows_updated")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "grade_windows"
        unique_together = ("school", "academic_year", "term_number", "form")

    def __str__(self):
        state = "Open" if self.is_open else "Closed"
        return f"{self.form} — {self.academic_year.name} Term {self.term_number} — {state}"


class Evaluation(models.Model):
    """An assessment created by a teacher before grades can be entered."""

    CATEGORY_CHOICES = [
        ("coursework", "Coursework"),
        ("exam", "Exam"),
    ]

    SUBCATEGORY_CHOICES = [
        ("test", "Test"),
        ("quiz", "Quiz"),
        ("project", "Project"),
        ("homework", "Homework"),
        ("assignment", "Assignment"),
        ("other", "Other"),
        ("final_exam", "Final Exam"),
        ("mock_exam", "Mock Exam"),
        ("midterm", "Midterm Exam"),
    ]

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="evaluations")
    section = models.ForeignKey("scheduling.Section", on_delete=models.CASCADE, related_name="evaluations")
    title = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    subcategory = models.CharField(max_length=20, choices=SUBCATEGORY_CHOICES)
    max_marks = models.DecimalField(max_digits=6, decimal_places=2)
    weight = models.DecimalField(max_digits=5, decimal_places=2, default=1.00)
    is_final_exam = models.BooleanField(default=False)
    date = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="evaluations_created")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "evaluations"
        ordering = ["date", "created_at"]

    def __str__(self):
        return f"{self.section} — {self.title}"

    def clean(self):
        if self.max_marks <= 0:
            raise ValidationError("Max marks must be greater than 0.")


class GradeEntry(models.Model):
    """One grade per student per evaluation. Null marks = absent."""

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="grade_entries")
    evaluation = models.ForeignKey(Evaluation, on_delete=models.CASCADE, related_name="grade_entries")
    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="grade_entries")
    marks_earned = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    is_absent = models.BooleanField(default=False)
    note = models.TextField(blank=True)
    entered_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="grade_entries_entered")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "grade_entries"
        unique_together = ("evaluation", "student")

    def __str__(self):
        return f"{self.student} — {self.evaluation.title} — {self.marks_earned}"

    @property
    def percentage(self):
        if self.is_absent or self.marks_earned is None:
            return None
        if self.evaluation.max_marks > 0:
            return round(float(self.marks_earned) / float(self.evaluation.max_marks) * 100, 1)
        return None


class ReportCard(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("published", "Published"),
    ]

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="report_cards")
    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="report_cards")
    academic_year = models.ForeignKey("scheduling.AcademicYear", on_delete=models.CASCADE, related_name="report_cards")
    term_number = models.PositiveIntegerField()
    gpa = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="draft")
    comment = models.TextField(blank=True)
    generated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="report_cards_generated")
    generated_at = models.DateTimeField(auto_now_add=True)
    pdf_file = models.FileField(upload_to="report_cards/", blank=True, null=True)

    class Meta:
        db_table = "report_cards"
        unique_together = ("student", "academic_year", "term_number")
        ordering = ["-academic_year__name", "term_number"]

    def __str__(self):
        return f"{self.student} — {self.academic_year.name} Term {self.term_number}"


class GradeVisibilityRule(models.Model):
    """
    Controls whether grades are visible in the student portal.
    student=None means school-wide rule.
    Per-student rule takes priority over school-wide rule.
    """

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="grade_visibility_rules")
    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, null=True, blank=True, related_name="grade_visibility_rules")
    is_visible = models.BooleanField(default=False)
    reason = models.TextField(blank=True)
    set_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="visibility_rules_set")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "grade_visibility_rules"

    def __str__(self):
        target = self.student or "School-wide"
        state = "Visible" if self.is_visible else "Hidden"
        return f"{target} — {state}"
