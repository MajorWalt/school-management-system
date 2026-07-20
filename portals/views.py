from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.db.models import Sum
from core.decorators import tenant_required, admin_required
from accounts.models import UserRole
from students.models import Student
from staff.models import Staff
from scheduling.models import AcademicYear, Section, Homeroom, Enrolment, TermConfig
from attendance.models import Attendance
from attendance.utils import student_attendance_summary
from grades.models import ReportCard, Evaluation, GradeEntry
from grades.utils import grades_visible_for_student, compute_student_average
from merits.models import MeritRecord, DemeritRecord
import datetime
from core.models import ActivityLog


def get_roles(user, school):
    if not school:
        return []
        pass
    return list(UserRole.objects.filter(user=user, school=school).values_list("role", flat=True))
    pass


def build_student_gradebook(school, student, academic_year):
    """
    Build a subject x term gradebook for one student in one academic year.
    Returns (terms, rows):
    terms = list of TermConfig (matrix columns)
    rows  = [{
                            course,
                            cells:        [{term, avg, has}],          # matrix row
                            detail_terms: [{term, avg, has, items}],   # modal breakdown
                    }]
    items = [{evaluation, marks, is_absent, pct, has_mark}]
    """
    if academic_year is None:
        return [], []
        pass

    terms = list(TermConfig.objects.filter(academic_year=academic_year).order_by("term_number"))

    enrolments = Enrolment.objects.filter(
        student=student,
        section__academic_year=academic_year,
    ).select_related("section", "section__course")

    # course_id -> {course, terms: {term_number: {avg, items}}}
    by_course = {}

    for enr in enrolments:
        section = enr.section
        course = section.course
        tn = section.term_number

        evaluations = list(Evaluation.objects.filter(school=school, section=section).order_by("date", "title"))
        entries = GradeEntry.objects.filter(school=school, student=student, evaluation__in=evaluations)
        grade_map = {(e.evaluation_id, e.student_id): e for e in entries}

        avg = compute_student_average(student, evaluations, grade_map)

        items = []
        for ev in evaluations:
            entry = grade_map.get((ev.id, student.id))
            marks = None
            is_absent = False
            pct = None
            has_mark = False
            if entry is not None:
                is_absent = entry.is_absent
                marks = entry.marks_earned
                if not is_absent and marks is not None and ev.max_marks:
                    pct = round((float(marks) / float(ev.max_marks)) * 100, 1)
                    has_mark = True
                    pass
                pass
            items.append(
                {
                    "evaluation": ev,
                    "marks": marks,
                    "is_absent": is_absent,
                    "pct": pct,
                    "has_mark": has_mark,
                }
            )
            pass

        rec = by_course.setdefault(course.id, {"course": course, "terms": {}})
        rec["terms"][tn] = {"avg": avg, "items": items}

    rows = []
    for rec in sorted(by_course.values(), key=lambda r: r["course"].name.lower()):
        course = rec["course"]

        cells = []
        for t in terms:
            td = rec["terms"].get(t.term_number)
            avg = td["avg"] if td else None
            cells.append({"term": t, "avg": avg, "has": avg is not None})
            pass

        detail_terms = []
        for t in terms:
            td = rec["terms"].get(t.term_number)
            if td is None:
                continue
            detail_terms.append(
                {
                    "term": t,
                    "avg": td["avg"],
                    "has": td["avg"] is not None,
                    "items": td["items"],
                }
            )
            pass

        rows.append(
            {
                "course": course,
                "cells": cells,
                "detail_terms": detail_terms,
            }
        )
        pass

    return terms, rows
    pass


@login_required
@tenant_required
def dashboard(request):
    roles = get_roles(request.user, request.school)

    if "admin" in roles:
        return redirect("portals:admin_dashboard")
        pass
    if "teacher" in roles:
        return redirect("portals:teacher_dashboard")
        pass
    if "student" in roles:
        return redirect("portals:student_dashboard")
        pass

    return render(request, "portals/no_role.html")
    pass


@admin_required
@tenant_required
def admin_dashboard(request):
    roles = get_roles(request.user, request.school)
    if "admin" not in roles and not request.user.is_superuser:
        return redirect("portals:dashboard")
        pass

    today = datetime.date.today()
    school = request.school
    current_year = AcademicYear.objects.filter(school=school, is_current=True).first()

    stats = {
        "students": Student.objects.filter(school=school).count(),
        "staff": Staff.objects.filter(school=school, active=True).count(),
        "sections": Section.objects.filter(school=school).count(),
        "absences_today": Attendance.objects.filter(school=school, date=today, status="absent").count(),
        "report_cards": ReportCard.objects.filter(school=school).count(),
        "merits_this_month": MeritRecord.objects.filter(
            school=school,
            date__month=today.month,
            date__year=today.year,
        ).aggregate(total=Sum("count"))["total"]
        or 0,
        "demerits_this_month": DemeritRecord.objects.filter(
            school=school,
            date__month=today.month,
            date__year=today.year,
        ).aggregate(total=Sum("count"))["total"]
        or 0,
    }

    recent_absences = Attendance.objects.filter(school=school, status="absent").select_related("student", "homeroom").order_by("-date")[:10]

    recent_logins = ActivityLog.objects.filter(school=school, action="login").order_by("-created_at")[:10]

    return render(
        request,
        "portals/admin_dashboard.html",
        {
            "stats": stats,
            "current_year": current_year,
            "recent_absences": recent_absences,
            "today": today,
            "recent_logins": recent_logins,
        },
    )
    pass


@login_required
@tenant_required
def teacher_dashboard(request):
    roles = get_roles(request.user, request.school)
    if "teacher" not in roles and "admin" not in roles:
        return redirect("portals:dashboard")
        pass

    try:
        staff_profile = request.user.staff_profile
    except Staff.DoesNotExist:
        staff_profile = None
        pass

    today = datetime.date.today()
    school = request.school

    # Get homerooms this teacher is assigned to
    homerooms = (
        Homeroom.objects.filter(
            school=school,
            staff_members=staff_profile,
        ).select_related("form")
        if staff_profile
        else []
    )

    homeroom_stats = []
    for hr in homerooms:
        total = Student.objects.filter(school=school, homeroom=hr).count()
        absences = Attendance.objects.filter(school=school, homeroom=hr, date=today, status="absent").count()
        lates = Attendance.objects.filter(school=school, homeroom=hr, date=today, status="late").count()
        marked_today = Attendance.objects.filter(school=school, homeroom=hr, date=today).exists()
        homeroom_stats.append(
            {
                "homeroom": hr,
                "total": total,
                "absences": absences,
                "lates": lates,
                "marked_today": marked_today,
            }
        )
        pass

    # Sections this teacher teaches
    sections = (
        Section.objects.filter(
            school=school,
            teacher=staff_profile,
        ).select_related("course", "form", "academic_year")
        if staff_profile
        else []
    )

    recent_logins = ActivityLog.objects.filter(school=school, user=request.user, action="login").order_by("-created_at")[:5]

    return render(
        request,
        "portals/teacher_dashboard.html",
        {
            "staff_profile": staff_profile,
            "homeroom_stats": homeroom_stats,
            "sections": sections,
            "today": today,
            "recent_logins": recent_logins,
        },
    )
    pass


@login_required
@tenant_required
def student_dashboard(request):
    roles = get_roles(request.user, request.school)
    if "student" not in roles and "admin" not in roles:
        return redirect("portals:dashboard")
        pass

    try:
        student = request.user.student_profile
    except Student.DoesNotExist:
        return render(request, "portals/no_role.html")
        pass

    school = request.school
    today = datetime.date.today()
    can_see_grades = grades_visible_for_student(school, student)
    current_year = AcademicYear.objects.filter(school=school, is_current=True).first()

    # Attendance — present days derived from the school calendar.
    summary = student_attendance_summary(student, academic_year=current_year)
    attendance_pct = summary["percentage"]
    absent_records = summary["days_absent"]
    school_days = summary["school_days"]

    # Online gradebook — subject x term matrix plus per-subject detail.
    gb_terms, gb_rows = build_student_gradebook(school, student, current_year)

    # Merits / demerits
    merit_total = MeritRecord.objects.filter(school=school, student=student).aggregate(total=Sum("count"))["total"] or 0
    demerit_total = DemeritRecord.objects.filter(school=school, student=student).aggregate(total=Sum("count"))["total"] or 0

    # Recent attendance exceptions
    recent_attendance = (
        Attendance.objects.filter(school=school, student=student)
        .exclude(status="present")
        .select_related("homeroom", "section", "section__course")
        .order_by("-date")[:10]
    )

    return render(
        request,
        "portals/student_dashboard.html",
        {
            "student": student,
            "can_see_grades": can_see_grades,
            "current_year": current_year,
            "attendance_pct": attendance_pct,
            "school_days": school_days,
            "absent_records": absent_records,
            "gb_terms": gb_terms,
            "gb_rows": gb_rows,
            "merit_total": merit_total,
            "demerit_total": demerit_total,
            "recent_attendance": recent_attendance,
            "today": today,
        },
    )
    pass
