from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from core.decorators import tenant_required
from .forms import (
	AcademicYearForm, CourseForm, EnrolmentForm,
	FormTermRuleForm, NonSchoolDayForm, SectionForm, TermConfigForm,
)
from .models import AcademicYear, Course, Enrolment, FormTermRule, NonSchoolDay, Section, TermConfig


# ── Academic Years ────────────────────────────────────────────────────────────

@login_required
@tenant_required
def year_list(request):
	years = AcademicYear.objects.filter(school=request.school).prefetch_related("term_configs", "form_term_rules")
	return render(request, "scheduling/year_list.html", {"years": years})


@login_required
@tenant_required
def year_add(request):
	form = AcademicYearForm(request.POST or None)
	if request.method == "POST" and form.is_valid():
		year = form.save(commit=False)
		year.school = request.school
		year.save()
		messages.success(request, f"Academic year {year.name} created.")
		return redirect("scheduling:year_list")
	return render(request, "scheduling/year_form.html", {"form": form, "title": "Add Academic Year"})


@login_required
@tenant_required
def year_edit(request, pk):
	year = get_object_or_404(AcademicYear, pk=pk, school=request.school)
	form = AcademicYearForm(request.POST or None, instance=year)
	if request.method == "POST" and form.is_valid():
		form.save()
		messages.success(request, f"Academic year {year.name} updated.")
		return redirect("scheduling:year_list")
	return render(request, "scheduling/year_form.html", {"form": form, "title": "Edit Academic Year", "year": year})


# ── Term Configs ──────────────────────────────────────────────────────────────

@login_required
@tenant_required
def term_add(request, year_pk):
	year = get_object_or_404(AcademicYear, pk=year_pk, school=request.school)
	form = TermConfigForm(request.POST or None)
	if request.method == "POST" and form.is_valid():
		term = form.save(commit=False)
		term.academic_year = year
		term.save()
		messages.success(request, f"{term.name} added to {year.name}.")
		return redirect("scheduling:year_list")
	return render(request, "scheduling/term_form.html", {"form": form, "year": year, "title": "Add Term"})


@login_required
@tenant_required
def term_edit(request, year_pk, pk):
	year = get_object_or_404(AcademicYear, pk=year_pk, school=request.school)
	term = get_object_or_404(TermConfig, pk=pk, academic_year=year)
	form = TermConfigForm(request.POST or None, instance=term)
	if request.method == "POST" and form.is_valid():
		form.save()
		messages.success(request, f"{term.name} updated.")
		return redirect("scheduling:year_list")
	return render(request, "scheduling/term_form.html", {"form": form, "year": year, "title": "Edit Term"})


# ── Form Term Rules ───────────────────────────────────────────────────────────

@login_required
@tenant_required
def rule_add(request, year_pk):
	year = get_object_or_404(AcademicYear, pk=year_pk, school=request.school)
	form = FormTermRuleForm(request.POST or None, school=request.school)
	if request.method == "POST" and form.is_valid():
		rule = form.save(commit=False)
		rule.academic_year = year
		rule.save()
		messages.success(request, "Rule added.")
		return redirect("scheduling:year_list")
	return render(request, "scheduling/rule_form.html", {"form": form, "year": year, "title": "Add Form Term Rule"})


@login_required
@tenant_required
def rule_edit(request, year_pk, pk):
	year = get_object_or_404(AcademicYear, pk=year_pk, school=request.school)
	rule = get_object_or_404(FormTermRule, pk=pk, academic_year=year)
	form = FormTermRuleForm(request.POST or None, instance=rule, school=request.school)
	if request.method == "POST" and form.is_valid():
		form.save()
		messages.success(request, "Rule updated.")
		return redirect("scheduling:year_list")
	return render(request, "scheduling/rule_form.html", {"form": form, "year": year, "title": "Edit Form Term Rule"})


# ── Non School Days ───────────────────────────────────────────────────────────

@login_required
@tenant_required
def non_school_day_list(request):
	days = NonSchoolDay.objects.filter(school=request.school)
	return render(request, "scheduling/nsd_list.html", {"days": days})


@login_required
@tenant_required
def non_school_day_add(request):
	form = NonSchoolDayForm(request.POST or None)
	if request.method == "POST" and form.is_valid():
		nsd = form.save(commit=False)
		nsd.school     = request.school
		nsd.created_by = request.user
		nsd.save()
		messages.success(request, f"{nsd.label} added.")
		return redirect("scheduling:nsd_list")
	return render(request, "scheduling/nsd_form.html", {"form": form, "title": "Add Non-School Day"})


@login_required
@tenant_required
def non_school_day_delete(request, pk):
	nsd = get_object_or_404(NonSchoolDay, pk=pk, school=request.school)
	nsd.delete()
	messages.warning(request, f"{nsd.label} removed.")
	return redirect("scheduling:nsd_list")


# ── Courses ───────────────────────────────────────────────────────────────────

@login_required
@tenant_required
def course_list(request):
	courses = Course.objects.filter(school=request.school)
	return render(request, "scheduling/course_list.html", {"courses": courses})


@login_required
@tenant_required
def course_add(request):
	form = CourseForm(request.POST or None)
	if request.method == "POST" and form.is_valid():
		course = form.save(commit=False)
		course.school = request.school
		course.save()
		messages.success(request, f"{course.name} added.")
		return redirect("scheduling:course_list")
	return render(request, "scheduling/course_form.html", {"form": form, "title": "Add Course"})


@login_required
@tenant_required
def course_edit(request, pk):
	course = get_object_or_404(Course, pk=pk, school=request.school)
	form   = CourseForm(request.POST or None, instance=course)
	if request.method == "POST" and form.is_valid():
		form.save()
		messages.success(request, f"{course.name} updated.")
		return redirect("scheduling:course_list")
	return render(request, "scheduling/course_form.html", {"form": form, "title": "Edit Course"})


# ── Sections ──────────────────────────────────────────────────────────────────

@login_required
@tenant_required
def section_list(request):
	year_pk  = request.GET.get("year")
	term     = request.GET.get("term")
	sections = Section.objects.filter(school=request.school).select_related("course", "form", "teacher", "academic_year")
	years    = AcademicYear.objects.filter(school=request.school)
	if year_pk:
		sections = sections.filter(academic_year_id=year_pk)
	if term:
		sections = sections.filter(term_number=term)
	return render(request, "scheduling/section_list.html", {
		"sections": sections,
		"years":    years,
		"selected_year": year_pk,
		"selected_term": term,
	})


@login_required
@tenant_required
def section_add(request):
	form = SectionForm(request.POST or None, school=request.school)
	if request.method == "POST" and form.is_valid():
		section = form.save(commit=False)
		section.school = request.school
		section.save()
		messages.success(request, f"Section created.")
		return redirect("scheduling:section_detail", pk=section.pk)
	return render(request, "scheduling/section_form.html", {"form": form, "title": "Add Section"})


@login_required
@tenant_required
def section_detail(request, pk):
	section    = get_object_or_404(Section, pk=pk, school=request.school)
	enrolments = section.enrolments.select_related("student")
	return render(request, "scheduling/section_detail.html", {
		"section":    section,
		"enrolments": enrolments,
	})


@login_required
@tenant_required
def section_edit(request, pk):
	section = get_object_or_404(Section, pk=pk, school=request.school)
	form    = SectionForm(request.POST or None, instance=section, school=request.school)
	if request.method == "POST" and form.is_valid():
		form.save()
		messages.success(request, "Section updated.")
		return redirect("scheduling:section_detail", pk=pk)
	return render(request, "scheduling/section_form.html", {"form": form, "title": "Edit Section"})


# ── Enrolments ────────────────────────────────────────────────────────────────

@login_required
@tenant_required
def enrol_student(request, section_pk):
	section = get_object_or_404(Section, pk=section_pk, school=request.school)
	form    = EnrolmentForm(request.POST or None, school=request.school)
	if request.method == "POST" and form.is_valid():
		enrolment = form.save(commit=False)
		enrolment.section = section
		enrolment.save()
		messages.success(request, f"{enrolment.student.get_full_name()} enrolled.")
		return redirect("scheduling:section_detail", pk=section_pk)
	return render(request, "scheduling/enrol_form.html", {"form": form, "section": section})


@login_required
@tenant_required
def enrolment_remove(request, pk):
	enrolment = get_object_or_404(Enrolment, pk=pk, section__school=request.school)
	section_pk = enrolment.section.pk
	enrolment.delete()
	messages.warning(request, "Student removed from section.")
	return redirect("scheduling:section_detail", pk=section_pk)