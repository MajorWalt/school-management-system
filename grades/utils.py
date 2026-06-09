from decimal import Decimal


def compute_student_average(student, evaluations, grade_entries_map):
	"""
	Weighted average for a student across evaluations.
	Absent entries and null marks are excluded from average.
	Returns percentage (0-100) or None if no valid grades.
	"""
	total_weight  = Decimal("0")
	weighted_sum  = Decimal("0")

	for ev in evaluations:
		entry = grade_entries_map.get((ev.pk, student.pk))
		if not entry:
			continue
		if entry.is_absent or entry.marks_earned is None:
			continue
		if ev.max_marks <= 0:
			continue
		pct = (entry.marks_earned / ev.max_marks) * 100
		weighted_sum  += pct * ev.weight
		total_weight  += ev.weight

	if total_weight == 0:
		return None

	return round(weighted_sum / total_weight, 1)


def grade_window_is_open(school, academic_year, term_number, form):
	"""Returns True if grades are open for entry for this form/term."""
	from .models import GradeWindow
	window = GradeWindow.objects.filter(
		school=school,
		academic_year=academic_year,
		term_number=term_number,
		form=form,
	).first()
	if window is None:
		return False  # closed by default
	return window.is_open


def grades_visible_for_student(school, student):
	from .models import GradeVisibilityRule
	student_rule = GradeVisibilityRule.objects.filter(
		school=school, student=student
	).order_by("-updated_at").first()
	if student_rule:
		return student_rule.is_visible
	school_rule = GradeVisibilityRule.objects.filter(
		school=school, student__isnull=True
	).order_by("-updated_at").first()
	if school_rule:
		return school_rule.is_visible
	return False