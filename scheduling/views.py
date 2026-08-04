from datetime import datetime
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from core.decorators import tenant_required, admin_required
from core.activity import log_activity
from students.models import Student, StudentStatusLog
from .forms import (
    AcademicYearForm,
    CourseForm,
    EnrolmentForm,
    FormTermRuleForm,
    NonSchoolDayForm,
    SectionForm,
    TermConfigForm,
)
from .models import AcademicYear, Course, Enrolment, Form, FormTermRule, Homeroom, NonSchoolDay, Section, TermConfig, YearPlacement


# ── Placement Processing Helpers ──────────────────────────────────────────────

STATUS_OUTCOME_MAP = {
    "transferred": "transferred",
    "withdrawn": "withdrawn",
    "graduated": "graduated",
    "not_graduated": "not_graduated",
}


def _process_exit_placements(request, post_data, new_year, outcome_counts, processed_students):
    """Process student exit choices (graduated, transferred, etc.)"""
    for key, value in post_data.items():
        if not (key.startswith("student_") and key.endswith("_exit") and value.startswith("exit_")):
            continue

        parts = key.split("_")
        student_id = int(parts[1])
        if student_id in processed_students:
            continue
        processed_students.add(student_id)

        student = get_object_or_404(Student, pk=student_id, school=request.school)
        exit_code = value.split("_", 1)[1]

        if exit_code in outcome_counts:
            outcome_counts[exit_code] += 1
            YearPlacement.objects.create(
                student=student,
                academic_year=new_year,
                outcome=exit_code,
                recorded_by=request.user,
            )

            if exit_code in STATUS_OUTCOME_MAP:
                StudentStatusLog.objects.create(
                    student=student,
                    academic_year=new_year,
                    status=STATUS_OUTCOME_MAP[exit_code],
                    change_date=datetime.now().date(),
                    reason="Year promotion - exit",
                    changed_by=request.user,
                )

            student.homeroom = None
            student.form = None
            student.save()


def _process_continuing_placements(request, post_data, new_year, outcome_counts, processed_students):
    """Process student continuing placements (new homeroom/form)"""
    for key, value in post_data.items():
        if not (key.startswith("student_") and key.endswith("_placement") and value):
            continue

        parts = key.split("_")
        student_id = int(parts[1])
        if student_id in processed_students:
            continue
        processed_students.add(student_id)

        student = get_object_or_404(Student, pk=student_id, school=request.school)
        try:
            homeroom_id = int(value)
            homeroom = get_object_or_404(Homeroom, pk=homeroom_id, school=request.school)
            outcome_counts["continuing"] += 1
            YearPlacement.objects.create(
                student=student,
                academic_year=new_year,
                outcome="continuing",
                homeroom=homeroom,
                recorded_by=request.user,
            )
            student.homeroom = homeroom
            student.form = homeroom.form
            student.save()
        except (ValueError, TypeError):
            pass


def _build_promotion_summary(outcome_counts):
    """Build a summary string of promotion outcomes."""
    summary = f"Promoted {outcome_counts['continuing']} continuing"
    if outcome_counts["transferred"] > 0:
        summary += f", {outcome_counts['transferred']} transferred"
    if outcome_counts["withdrawn"] > 0:
        summary += f", {outcome_counts['withdrawn']} withdrawn"
    if outcome_counts["graduated"] > 0:
        summary += f", {outcome_counts['graduated']} graduated"
    if outcome_counts["not_graduated"] > 0:
        summary += f", {outcome_counts['not_graduated']} not graduated"
    return summary


# ── Academic Years ────────────────────────────────────────────────────────────


@admin_required
def year_list(request):
    years = AcademicYear.objects.filter(school=request.school).prefetch_related("term_configs", "form_term_rules")
    return render(request, "scheduling/year_list.html", {"years": years})


@admin_required
def year_add(request):
    form = AcademicYearForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        year = form.save(commit=False)
        year.school = request.school
        year.save()
        messages.success(request, f"Academic year {year.name} created.")
        return redirect("scheduling:year_list")
    return render(request, "scheduling/year_form.html", {"form": form, "title": "Add Academic Year"})


@admin_required
def year_edit(request, pk):
    year = get_object_or_404(AcademicYear, pk=pk, school=request.school)
    form = AcademicYearForm(request.POST or None, instance=year)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Academic year {year.name} updated.")
        return redirect("scheduling:year_list")
    return render(request, "scheduling/year_form.html", {"form": form, "title": "Edit Academic Year", "year": year})


# ── Term Configs ──────────────────────────────────────────────────────────────


@admin_required
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


@admin_required
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


@admin_required
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


@admin_required
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


@admin_required
def non_school_day_list(request):
    days = NonSchoolDay.objects.filter(school=request.school)
    return render(request, "scheduling/nsd_list.html", {"days": days})


@admin_required
def non_school_day_add(request):
    form = NonSchoolDayForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        nsd = form.save(commit=False)
        nsd.school = request.school
        nsd.created_by = request.user
        nsd.save()
        messages.success(request, f"{nsd.label} added.")
        return redirect("scheduling:nsd_list")
    return render(request, "scheduling/nsd_form.html", {"form": form, "title": "Add Non-School Day"})


@admin_required
def non_school_day_delete(request, pk):
    nsd = get_object_or_404(NonSchoolDay, pk=pk, school=request.school)
    nsd.delete()
    messages.warning(request, f"{nsd.label} removed.")
    return redirect("scheduling:nsd_list")


# ── Courses ───────────────────────────────────────────────────────────────────


@admin_required
def course_list(request):
    query = request.GET.get("q", "")
    area = request.GET.get("area", "")
    courses = Course.objects.filter(school=request.school)

    if query:
        from django.db.models import Q

        courses = courses.filter(Q(name__icontains=query) | Q(code__icontains=query) | Q(faculty__icontains=query))
    if area:
        courses = courses.filter(subject_area=area)

    return render(
        request,
        "scheduling/course_list.html",
        {
            "courses": courses,
            "query": query,
            "selected_area": area,
            "subject_areas": Course.SUBJECT_AREA_CHOICES,
        },
    )


@admin_required
def course_add(request):
    form = CourseForm(request.POST or None, school=request.school)
    if request.method == "POST" and form.is_valid():
        course = form.save(commit=False)
        course.school = request.school
        course.save()
        messages.success(request, f"{course.name} added.")
        return redirect("scheduling:course_detail", pk=course.pk)
    return render(
        request,
        "scheduling/course_form.html",
        {
            "form": form,
            "title": "Add Course",
        },
    )


@admin_required
def course_detail(request, pk):
    course = get_object_or_404(Course, pk=pk, school=request.school)
    sections = Section.objects.filter(school=request.school, course=course).select_related("academic_year", "form", "teacher")
    return render(
        request,
        "scheduling/course_detail.html",
        {
            "course": course,
            "sections": sections,
        },
    )


@admin_required
def course_edit(request, pk):
    course = get_object_or_404(Course, pk=pk, school=request.school)
    form = CourseForm(request.POST or None, instance=course, school=request.school)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"{course.name} updated.")
        return redirect("scheduling:course_detail", pk=pk)
    return render(
        request,
        "scheduling/course_form.html",
        {
            "form": form,
            "title": f"Edit — {course.name}",
            "course": course,
        },
    )


@admin_required
def course_delete(request, pk):
    course = get_object_or_404(Course, pk=pk, school=request.school)
    if request.method == "POST":
        name = course.name
        course.delete()
        messages.warning(request, f"Course '{name}' deleted.")
        return redirect("scheduling:course_list")
    return render(request, "scheduling/course_confirm_delete.html", {"course": course})


# ── Sections ──────────────────────────────────────────────────────────────────


@admin_required
def section_list(request):
    year_pk = request.GET.get("year")
    term = request.GET.get("term")
    sections = Section.objects.filter(school=request.school).select_related("course", "form", "teacher", "academic_year")
    years = AcademicYear.objects.filter(school=request.school)
    if year_pk:
        sections = sections.filter(academic_year_id=year_pk)
    if term:
        sections = sections.filter(term_number=term)
    return render(
        request,
        "scheduling/section_list.html",
        {
            "sections": sections,
            "years": years,
            "selected_year": year_pk,
            "selected_term": term,
        },
    )


@admin_required
def section_add(request):
    form = SectionForm(request.POST or None, school=request.school)
    if request.method == "POST" and form.is_valid():
        section = form.save(commit=False)
        section.school = request.school
        section.save()
        log_activity(request, "section_created", f"Created section: {section}.")
        messages.success(request, "Section created.")
        return redirect("scheduling:section_detail", pk=section.pk)
    return render(request, "scheduling/section_form.html", {"form": form, "title": "Add Section"})


@admin_required
def section_detail(request, pk):
    section = get_object_or_404(Section, pk=pk, school=request.school)
    enrolments = section.enrolments.select_related("student")
    return render(
        request,
        "scheduling/section_detail.html",
        {
            "section": section,
            "enrolments": enrolments,
        },
    )


@admin_required
def section_edit(request, pk):
    section = get_object_or_404(Section, pk=pk, school=request.school)
    form = SectionForm(request.POST or None, instance=section, school=request.school)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Section updated.")
        return redirect("scheduling:section_detail", pk=pk)
    return render(request, "scheduling/section_form.html", {"form": form, "title": "Edit Section"})


# ── Enrolments ────────────────────────────────────────────────────────────────


@admin_required
def enrol_student(request, section_pk):
    section = get_object_or_404(Section, pk=section_pk, school=request.school)
    form = EnrolmentForm(request.POST or None, school=request.school)
    if request.method == "POST" and form.is_valid():
        enrolment = form.save(commit=False)
        enrolment.section = section
        enrolment.save()
        log_activity(request, "enrolment_added", f"Enrolled {enrolment.student.get_full_name()} in section {section}.")
        messages.success(request, f"{enrolment.student.get_full_name()} enrolled.")
        return redirect("scheduling:section_detail", pk=section_pk)
    return render(request, "scheduling/enrol_form.html", {"form": form, "section": section})


@admin_required
def enrolment_remove(request, pk):
    enrolment = get_object_or_404(Enrolment, pk=pk, section__school=request.school)
    section_pk = enrolment.section.pk
    enrolment.delete()
    messages.warning(request, "Student removed from section.")
    return redirect("scheduling:section_detail", pk=section_pk)


# ── Academic Year Promotion Wizard ────────────────────────────────────────────


@admin_required
def year_new(request):
    """Step 1: Gather new academic year details (buffer in session, don't create yet)."""
    form = AcademicYearForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        # Store cleaned data in session under a dedicated key
        request.session["wizard_new_year"] = {
            "name": form.cleaned_data["name"],
            "is_current": form.cleaned_data.get("is_current", False),
            "start_date": form.cleaned_data["start_date"].isoformat() if form.cleaned_data.get("start_date") else None,
            "end_date": form.cleaned_data["end_date"].isoformat() if form.cleaned_data.get("end_date") else None,
        }
        return redirect("scheduling:year_promote")
    return render(
        request,
        "scheduling/year_form.html",
        {"form": form, "title": "Add Academic Year", "wizard_step": 1},
    )


@admin_required
def year_promote(request):
    """Step 2: Show promotion grid and process student placements."""
    # Check for session buffer
    wizard_data = request.session.get("wizard_new_year")
    if not wizard_data:
        messages.warning(request, "Session expired. Please start over.")
        return redirect("scheduling:year_new")

    # Get source (active) academic year
    from attendance.utils import get_active_academic_year

    source_year = get_active_academic_year(request.school)
    if not source_year:
        messages.error(request, "No active academic year found to promote from.")
        return redirect("scheduling:year_new")

    # Build forms/homerooms map for Alpine cascade
    forms = Form.objects.filter(school=request.school).order_by("order")
    forms_list = list(forms)
    forms_data = {}
    for form in forms_list:
        homerooms = Homeroom.objects.filter(school=request.school, form=form).values_list("id", "name")
        forms_data[form.id] = [{"id": str(hid), "name": hname} for hid, hname in homerooms]

    # Get active students (enrolled + not terminal status)
    active_students = (
        Student.objects.filter(school=request.school, homeroom__isnull=False)
        .select_related("form", "homeroom")
        .order_by("homeroom__form__order", "homeroom__name", "last_name", "first_name")
    )

    # Filter by status: only those with non-terminal status
    active_students_list = [s for s in active_students if s.current_status() not in ["graduated", "transferred", "withdrawn", "on_leave"]]

    # Group by form → homeroom
    grouped = {}
    for student in active_students_list:
        if student.homeroom:
            form_id = student.form.id
            form_name = student.form.name
            homeroom_id = student.homeroom.id
            homeroom_name = student.homeroom.name

            form_key = (form_id, form_name)
            homeroom_key = (homeroom_id, homeroom_name)
            if form_key not in grouped:
                grouped[form_key] = {}
            if homeroom_key not in grouped[form_key]:
                grouped[form_key][homeroom_key] = []
            grouped[form_key][homeroom_key].append(student)

    if request.method == "POST":
        try:
            with transaction.atomic():
                # 1. Create new AcademicYear
                new_year_data = {
                    "name": wizard_data["name"],
                    "is_current": wizard_data.get("is_current", False),
                    "school": request.school,
                }
                if wizard_data.get("start_date"):
                    new_year_data["start_date"] = datetime.fromisoformat(wizard_data["start_date"]).date()
                if wizard_data.get("end_date"):
                    new_year_data["end_date"] = datetime.fromisoformat(wizard_data["end_date"]).date()

                new_year = AcademicYear.objects.create(**new_year_data)

                # Count placements by outcome
                outcome_counts = {
                    "continuing": 0,
                    "transferred": 0,
                    "withdrawn": 0,
                    "graduated": 0,
                    "not_graduated": 0,
                }

                # 2. Backfill YearPlacement for source year (idempotent)
                for student in active_students_list:
                    YearPlacement.objects.get_or_create(
                        student=student,
                        academic_year=source_year,
                        defaults={
                            "homeroom": student.homeroom,
                            "outcome": "continuing",
                            "recorded_by": request.user,
                        },
                    )

                # 3. Process student placements
                processed_students = set()
                _process_exit_placements(request, request.POST, new_year, outcome_counts, processed_students)
                _process_continuing_placements(request, request.POST, new_year, outcome_counts, processed_students)

                # 4. Log activity
                summary = _build_promotion_summary(outcome_counts)
                log_activity(request, "year_promotion", summary)

                # Clear session buffer
                del request.session["wizard_new_year"]
                request.session.modified = True

                messages.success(request, f"Academic year {new_year.name} created and students promoted.")
                return redirect("scheduling:year_list")

        except Exception as e:
            messages.error(request, f"Promotion failed: {str(e)}")
            return redirect("scheduling:year_new")

    return render(
        request,
        "scheduling/year_promote.html",
        {
            "source_year": source_year,
            "new_year_name": wizard_data["name"],
            "forms_data": forms_data,
            "forms_list": forms_list,
            "grouped": grouped,
            "wizard_step": 2,
        },
    )
