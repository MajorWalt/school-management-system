from django.db import models
from django.core.exceptions import ValidationError
from core.models import School
from accounts.models import User


class GradeEntry(models.Model):

	CATEGORY_CHOICES = [
		("coursework", "Coursework"),
		("exam",       "Exam"),
		("quiz",       "Quiz"),
		("project",    "Project"),
		("other",      "Other"),
	]

	school        = models.ForeignKey(School, on_delete=models.CASCADE, related_name="grade_entries")
	enrolment     = models.ForeignKey("scheduling.Enrolment", on_delete=models.CASCADE, related_name="grade_entries")
	category      = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
	title         = models.CharField(max_length=100)
	max_marks     = models.DecimalField(max_digits=6, decimal_places=2)
	marks_earned  = models.DecimalField(max_digits=6, decimal_places=2)
	weight        = models.DecimalField(max_digits=5, decimal_places=2, default=1.00)
	is_final_exam = models.BooleanField(default=False)
	date          = models.DateField(null=True, blank=True)
	note          = models.TextField(blank=True)
	entered_by    = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="grade_entries")
	created_at    = models.DateTimeField(auto_now_add=True)
	updated_at    = models.DateTimeField(auto_now=True)

	class Meta:
		db_table = "grade_entries"
		ordering = ["-date", "title"]

	def __str__(self):
		return f"{self.enrolment.student} — {self.title} ({self.marks_earned}/{self.max_marks})"

	def clean(self):
		if self.marks_earned is not None and self.max_marks is not None:
			if self.marks_earned > self.max_marks:
				raise ValidationError("Marks earned cannot exceed max marks.")

	def save(self, *args, **kwargs):
		self.full_clean()
		super().save(*args, **kwargs)

	@property
	def percentage(self):
		if self.max_marks:
			return round((self.marks_earned / self.max_marks) * 100, 2)
		return 0


class GradeVisibilityRule(models.Model):
	"""
	Controls whether grades are visible in the student portal.
	student=None means school-wide rule.
	Per-student rule takes priority over school-wide rule.
	"""
	school      = models.ForeignKey(School, on_delete=models.CASCADE, related_name="grade_visibility_rules")
	student     = models.ForeignKey("students.Student", on_delete=models.CASCADE,
									null=True, blank=True, related_name="grade_visibility_rules")
	is_visible  = models.BooleanField(default=False)
	reason      = models.TextField(blank=True)
	set_by      = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="visibility_rules_set")
	created_at  = models.DateTimeField(auto_now_add=True)
	updated_at  = models.DateTimeField(auto_now=True)

	class Meta:
		db_table = "grade_visibility_rules"

	def __str__(self):
		target = self.student or "School-wide"
		state  = "Visible" if self.is_visible else "Hidden"
		return f"{target} — {state}"


class ReportCard(models.Model):

	STATUS_CHOICES = [
		("draft",     "Draft"),
		("published", "Published"),
	]

	school          = models.ForeignKey(School, on_delete=models.CASCADE, related_name="report_cards")
	student         = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="report_cards")
	academic_year   = models.ForeignKey("scheduling.AcademicYear", on_delete=models.CASCADE, related_name="report_cards")
	term_number     = models.PositiveIntegerField()
	gpa             = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
	status          = models.CharField(max_length=10, choices=STATUS_CHOICES, default="draft")
	generated_by    = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="report_cards_generated")
	generated_at    = models.DateTimeField(auto_now_add=True)
	pdf_file        = models.FileField(upload_to="report_cards/", blank=True, null=True)

	class Meta:
		db_table        = "report_cards"
		unique_together = ("student", "academic_year", "term_number")
		ordering        = ["-academic_year__name", "term_number"]

	def __str__(self):
		return f"{self.student} — {self.academic_year.name} Term {self.term_number}"