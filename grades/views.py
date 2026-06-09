from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from core.decorators import tenant_required
from scheduling.models import AcademicYear, Enrolment, Section
from students.models import Student
from .forms import GradeEntryForm, GradeVisibilityForm
from .models import GradeEntry, GradeVisibilityRule, ReportCard
from .utils import compute_term_grade, grades_visible_for_student


@login_required
@tenant_required
def grade_section_select(request):
	"""Pick a section to enter grades for."""
	sections = Section.objects.filter(
		school=request.school
	).select_related("course", "form", "academic_year")
	return render(request, "grades/section_select.html", {"sections": sections})


@login_required
@tenant_required
def grade_section_overview(request, section_pk):
	"""Overview of all enrolled students and their term grade summary."""
	section    = get_object_or_404(Section, pk=section_pk, school=request.school)
	enrolments = section.enrolments.select_related("student")

	rows = []
	for enrolment in enrolments:
		result = compute_term_grade(enrolment)
		rows.append({
			"enrolment": enrolment,
			"student":   enrolment.student,
			"result":    result,
		})

	return render(request, "grades/section_overview.html", {
		"section": section,
		"rows":    rows,
	})


@login_required
@tenant_required
def grade_enrolment_detail(request, enrolment_pk):
	"""View and add grade entries for a single student enrolment."""
	enrolment = get_object_or_404(
		Enrolment, pk=enrolment_pk, section__school=request.school
	)
	entries = enrolment.grade_entries.all()
	result  = compute_term_grade(enrolment)
	form    = GradeEntryForm(request.POST or None)

	if request.method == "POST" and form.is_valid():
		entry = form.save(commit=False)
		entry.school     = request.school
		entry.enrolment  = enrolment
		entry.entered_by = request.user
		entry.save()
		messages.success(request, f"Grade entry '{entry.title}' saved.")
		return redirect("grades:enrolment_detail", enrolment_pk=enrolment_pk)

	return render(request, "grades/enrolment_detail.html", {
		"enrolment": enrolment,
		"entries":   entries,
		"result":    result,
		"form":      form,
	})


@login_required
@tenant_required
def grade_entry_delete(request, pk):
	entry      = get_object_or_404(GradeEntry, pk=pk, school=request.school)
	enrolment_pk = entry.enrolment.pk
	entry.delete()
	messages.warning(request, "Grade entry deleted.")
	return redirect("grades:enrolment_detail", enrolment_pk=enrolment_pk)


# ── Visibility ────────────────────────────────────────────────────────────────

@login_required
@tenant_required
def visibility_overview(request):
	"""School-wide and per-student grade visibility controls."""
	students    = Student.objects.filter(school=request.school)
	school_rule = GradeVisibilityRule.objects.filter(
		school=request.school, student__isnull=True
	).order_by("-updated_at").first()

	student_rules = GradeVisibilityRule.objects.filter(
		school=request.school, student__isnull=False
	).select_related("student").order_by("student__last_name")

	return render(request, "grades/visibility_overview.html", {
		"school_rule":    school_rule,
		"student_rules":  student_rules,
		"students":       students,
	})


@login_required
@tenant_required
def visibility_set_school(request):
	"""Set school-wide visibility rule."""
	existing = GradeVisibilityRule.objects.filter(
		school=request.school, student__isnull=True
	).order_by("-updated_at").first()

	form = GradeVisibilityForm(request.POST or None, instance=existing)
	if request.method == "POST" and form.is_valid():
		rule = form.save(commit=False)
		rule.school  = request.school
		rule.student = None
		rule.set_by  = request.user
		if existing:
			existing.is_visible = rule.is_visible
			existing.reason     = rule.reason
			existing.set_by     = request.user
			existing.save()
		else:
			rule.save()
		messages.success(request, "School-wide visibility updated.")
		return redirect("grades:visibility")
	return render(request, "grades/visibility_form.html", {
		"form":  form,
		"title": "School-wide Grade Visibility",
	})


@login_required
@tenant_required
def visibility_set_student(request, student_pk):
	"""Set per-student visibility override."""
	student  = get_object_or_404(Student, pk=student_pk, school=request.school)
	existing = GradeVisibilityRule.objects.filter(
		school=request.school, student=student
	).order_by("-updated_at").first()

	form = GradeVisibilityForm(request.POST or None, instance=existing)
	if request.method == "POST" and form.is_valid():
		rule = form.save(commit=False)
		rule.school  = request.school
		rule.student = student
		rule.set_by  = request.user
		if existing:
			existing.is_visible = rule.is_visible
			existing.reason     = rule.reason
			existing.set_by     = request.user
			existing.save()
		else:
			rule.save()
		messages.success(request, f"Visibility updated for {student.get_full_name()}.")
		return redirect("grades:visibility")
	return render(request, "grades/visibility_form.html", {
		"form":    form,
		"title":   f"Grade Visibility — {student.get_full_name()}",
		"student": student,
	})


# ── Report Cards ──────────────────────────────────────────────────────────────

@login_required
@tenant_required
def report_card_list(request):
	year_pk      = request.GET.get("year")
	term         = request.GET.get("term")
	report_cards = ReportCard.objects.filter(
		school=request.school
	).select_related("student", "academic_year")
	years        = AcademicYear.objects.filter(school=request.school)

	if year_pk:
		report_cards = report_cards.filter(academic_year_id=year_pk)
	if term:
		report_cards = report_cards.filter(term_number=term)

	return render(request, "grades/report_card_list.html", {
		"report_cards":  report_cards,
		"years":         years,
		"selected_year": year_pk,
		"selected_term": term,
	})


@login_required
@tenant_required
def report_card_generate(request, section_pk):
	"""Generate report cards for all students in a section."""
	section    = get_object_or_404(Section, pk=section_pk, school=request.school)
	enrolments = section.enrolments.select_related("student")
	created    = 0

	for enrolment in enrolments:
		result = compute_term_grade(enrolment)
		if result is None:
			continue

		obj, _ = ReportCard.objects.update_or_create(
			school        = request.school,
			student       = enrolment.student,
			academic_year = section.academic_year,
			term_number   = section.term_number,
			defaults={
				"gpa":          result["term_grade"],
				"status":       "draft",
				"generated_by": request.user,
			}
		)
		created += 1

	messages.success(request, f"{created} report card(s) generated as draft.")
	return redirect("grades:report_card_list")


@login_required
@tenant_required
def report_card_publish(request, pk):
	rc = get_object_or_404(ReportCard, pk=pk, school=request.school)
	rc.status = "published"
	rc.save()
	messages.success(request, f"Report card published for {rc.student.get_full_name()}.")
	return redirect("grades:report_card_list")


@login_required
@tenant_required
def report_card_detail(request, pk):
	rc         = get_object_or_404(ReportCard, pk=pk, school=request.school)
	enrolments = Enrolment.objects.filter(
		student=rc.student,
		section__academic_year=rc.academic_year,
		section__term_number=rc.term_number,
		section__school=request.school,
	).select_related("section__course")

	rows = []
	for enrolment in enrolments:
		result = compute_term_grade(enrolment)
		rows.append({
			"course": enrolment.section.course,
			"result": result,
		})

	return render(request, "grades/report_card_detail.html", {
		"rc":   rc,
		"rows": rows,
	})