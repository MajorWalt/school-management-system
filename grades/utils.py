from decimal import Decimal


def compute_student_average(student, evaluations, grade_entries_map):
	"""
	Weighted average for a student across evaluations.
	Absent entries and null marks are excluded from average.
	Returns percentage (0-100) or None if no valid grades.
	"""
	total_weight = Decimal("0")
	weighted_sum = Decimal("0")

	for ev in evaluations:
		entry = grade_entries_map.get((ev.pk, student.pk))
		if not entry:
			continue
		if entry.is_absent or entry.marks_earned is None:
			continue
		if ev.max_marks <= 0:
			continue

		marks = Decimal(str(entry.marks_earned))
		max_m = Decimal(str(ev.max_marks))
		weight = Decimal(str(ev.weight))

		# Cap marks at max_marks — prevents > 100%
		if marks > max_m:
			marks = max_m

		pct = (marks / max_m) * Decimal("100")
		weighted_sum += pct * weight
		total_weight += weight

	if total_weight == 0:
		return None

	result = weighted_sum / total_weight

	# Safety cap — should never exceed 100 but guard anyway
	if result > Decimal("100"):
		result = Decimal("100")

	return round(result, 1)


def grade_window_is_open(school, academic_year, term_number, form):
	from .models import GradeWindow
	window = GradeWindow.objects.filter(
		school=school,
		academic_year=academic_year,
		term_number=term_number,
		form=form,
	).first()
	if window is None:
		return False
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