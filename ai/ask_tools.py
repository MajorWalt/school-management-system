"""
Read-only tools for Ask AI.
Every query is scoped to the current school. Tools default to the active academic year and accept
an optional past year; student_history and subject_trend span all years.
Non-admins only see sections they taught (any year), plus their departments' sections if they are HODs.
At-risk data is admin-only. Teacher-to-course assignments (teacher_courses) are visible to all staff.
Tools return compact JSON strings for the model.
"""

import json
import logging

from django.db.models import Max, Q, Sum

from accounts.utils import is_admin
from analytics.models import AtRiskScore
from attendance.utils import get_active_academic_year
from grades.models import Evaluation
from grades.term_grades import load_section_grades, load_term_weights, section_term_grade, weights_for
from grades.views import get_hod_departments, get_teacher_staff
from merits.models import DemeritRecord, MeritRecord
from scheduling.models import AcademicYear, Enrolment, Section
from students.models import Student

from .comments import DEFAULT_PASS_MARK, get_pass_mark

logger = logging.getLogger(__name__)

MAX_ROWS = 60
PASS_MARK_NOTE = "Pass marks are the current per-form settings, applied to every year."


def _latest_term(school, year):
    """Latest term in a year that has any evaluations (1 if none)."""
    if not year:
        return None
    latest = Evaluation.objects.filter(school=school, section__academic_year=year).aggregate(m=Max("section__term_number"))["m"]
    return latest or 1
    pass


class AskScope:
    """Who is asking and what they are allowed to see."""

    def __init__(self, user, school):
        self.user = user
        self.school = school
        self.is_admin = is_admin(user, school)
        self.staff = get_teacher_staff(user)
        self.hod_departments = get_hod_departments(self.staff)
        self.year = get_active_academic_year(school)
        self.years = list(AcademicYear.objects.filter(school=school).order_by("name"))
        self.current_term = _latest_term(school, self.year)
        pass

    @property
    def role_label(self):
        if self.is_admin:
            return "an administrator"
        if self.hod_departments:
            return f"a teacher and head of department ({', '.join(self.hod_departments)})"
        if self.staff:
            return "a teacher"
        return "a staff member"
        pass

    def resolve_year(self, name):
        """(AcademicYear, error). Blank name = active year."""
        if name is None or not str(name).strip():
            if self.year:
                return self.year, None
            return None, "No active academic year is set."
        wanted = str(name).strip().lower()
        for y in self.years:
            if y.name.lower() == wanted:
                return y, None
        matches = [y for y in self.years if wanted in y.name.lower()]
        if len(matches) == 1:
            return matches[0], None
        on_record = ", ".join(y.name for y in self.years) or "none"
        return None, f"Unknown academic year '{name}'. Years on record: {on_record}."
        pass

    def _role_filter(self, qs):
        if self.is_admin:
            return qs
        if not self.staff:
            return qs.none()
        q = Q(teacher=self.staff)
        if self.hod_departments:
            q |= Q(course__department__in=self.hod_departments)
        return qs.filter(q)
        pass

    def all_sections(self):
        """Accessible sections in every year."""
        qs = Section.objects.filter(school=self.school).select_related("course", "form", "teacher", "academic_year")
        return self._role_filter(qs)
        pass

    def sections(self, year=None):
        """Accessible sections in one year (default: active year)."""
        year = year or self.year
        if not year:
            return Section.objects.none()
        return self.all_sections().filter(academic_year=year)
        pass

    def students(self):
        """Students the user can access (any year)."""
        qs = Student.objects.filter(school=self.school)
        if self.is_admin:
            return qs
        return qs.filter(enrolments__section__in=self.all_sections()).distinct()
        pass


def _int(value):
    try:
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None
    pass


def _mean(values):
    vals = [v for v in values if v is not None]
    return round(sum(vals) / len(vals), 1) if vals else None
    pass


def _term_grades(scope, sections, student_ids=None):
    """
    (grades, students) for the given sections (any mix of years).
    grades   = {(section_id, student_id): term_grade}  (only graded students)
    students = {student_id: Student}                   (every enrolled student)
    """
    sections = list(sections)
    if not sections:
        return {}, {}
    evals_by_section, grade_map = load_section_grades(scope.school, [s.pk for s in sections], student_ids)
    weights_map = load_term_weights(scope.school, sections)
    section_by_id = {s.pk: s for s in sections}

    enrolments = Enrolment.objects.filter(section__in=sections).select_related("student", "student__form")
    if student_ids is not None:
        enrolments = enrolments.filter(student_id__in=student_ids)

    grades = {}
    students = {}
    for e in enrolments:
        students[e.student_id] = e.student
        section = section_by_id[e.section_id]
        evs = evals_by_section.get(section.pk, [])
        if not evs:
            continue
        g = section_term_grade(e.student, evs, grade_map, weights_for(weights_map, section))
        if g is not None:
            grades[(section.pk, e.student_id)] = g
    return grades, students
    pass


def _find_student(scope, student_id):
    return scope.students().select_related("form", "homeroom").filter(student_id=str(student_id or "").strip()).first()
    pass


# -- Tools ---------------------------------------------------------------------


def find_students(scope, query=""):
    q = (query or "").strip()
    if len(q) < 2:
        return {"error": "Search text is too short."}
    qs = scope.students().select_related("form", "homeroom")
    for part in q.split():
        qs = qs.filter(Q(first_name__icontains=part) | Q(middle_name__icontains=part) | Q(last_name__icontains=part) | Q(student_id__iexact=part))
    rows = [
        {
            "student_id": s.student_id,
            "name": s.get_full_name(),
            "current_form": s.form.name if s.form else None,
            "current_homeroom": s.homeroom.name if s.homeroom else None,
        }
        for s in qs[:15]
    ]
    return {"count": len(rows), "students": rows}
    pass


def student_overview(scope, student_id="", year=None):
    student = _find_student(scope, student_id)
    if not student:
        return {"error": "No student with that ID that you can access."}
    year_obj, error = scope.resolve_year(year)
    if error:
        return {"error": error}

    sections = list(scope.sections(year_obj).filter(enrolments__student=student).order_by("course__name", "term_number"))
    grades, _ = _term_grades(scope, sections, [student.pk])

    subjects = {}
    forms = set()
    for s in sections:
        forms.add(s.form.name)
        subjects.setdefault(s.course.name, {})[f"term_{s.term_number}"] = grades.get((s.pk, student.pk))
    for terms in subjects.values():
        terms["year_average"] = _mean(terms.values())

    merits = MeritRecord.objects.filter(school=scope.school, student=student, academic_year=year_obj).aggregate(t=Sum("count"))["t"] or 0
    demerits = DemeritRecord.objects.filter(school=scope.school, student=student, academic_year=year_obj).aggregate(t=Sum("count"))["t"] or 0
    status = student.status_for_year(year_obj)

    data = {
        "name": student.get_full_name(),
        "student_id": student.student_id,
        "academic_year": year_obj.name,
        "form_that_year": ", ".join(sorted(forms)) or None,
        "current_homeroom": student.homeroom.name if student.homeroom else None,
        "status_that_year": dict(Student.STATUS_CHOICES).get(status, status),
        "pass_mark": get_pass_mark(scope.school, student.form) if student.form else DEFAULT_PASS_MARK,
        "subjects": subjects,
        "merits": merits,
        "demerits": demerits,
    }
    if scope.is_admin and year_obj == scope.year:
        risk = AtRiskScore.objects.filter(school=scope.school, student=student).order_by("-computed_on").first()
        if risk:
            data["at_risk"] = {
                "score": float(risk.score),
                "band": risk.band,
                "computed_on": str(risk.computed_on),
                "top_factors": risk.top_factors,
            }
    if not scope.is_admin:
        data["note"] = "Only subjects in sections this user taught or oversees are included."
    return data
    pass


def student_history(scope, student_id=""):
    """One student across every year on record."""
    student = _find_student(scope, student_id)
    if not student:
        return {"error": "No student with that ID that you can access."}

    sections = list(scope.all_sections().filter(enrolments__student=student).order_by("academic_year__name", "course__name", "term_number"))
    grades, _ = _term_grades(scope, sections, [student.pk])

    years = {}
    for s in sections:
        y = years.setdefault(s.academic_year.name, {"forms": set(), "subjects": {}, "counted": set()})
        y["forms"].add(s.form.name)
        g = grades.get((s.pk, student.pk))
        if g is None:
            continue
        y["subjects"].setdefault(s.course.name, []).append(g)
        if s.course.calc_average:
            y["counted"].add(s.course.name)

    merit_totals = {
        r["academic_year__name"]: r["t"]
        for r in MeritRecord.objects.filter(school=scope.school, student=student, academic_year__isnull=False).values("academic_year__name").annotate(t=Sum("count"))
    }
    demerit_totals = {
        r["academic_year__name"]: r["t"]
        for r in DemeritRecord.objects.filter(school=scope.school, student=student, academic_year__isnull=False).values("academic_year__name").annotate(t=Sum("count"))
    }

    rows = []
    for name in sorted(years):
        y = years[name]
        subject_avgs = {subj: _mean(vals) for subj, vals in y["subjects"].items()}
        rows.append(
            {
                "academic_year": name,
                "form": ", ".join(sorted(y["forms"])),
                "overall_average": _mean([avg for subj, avg in subject_avgs.items() if subj in y["counted"]]),
                "subject_averages": subject_avgs,
                "merits": merit_totals.get(name, 0),
                "demerits": demerit_totals.get(name, 0),
            }
        )

    data = {"name": student.get_full_name(), "student_id": student.student_id, "years": rows}
    if not scope.is_admin:
        data["note"] = "Only subjects in sections this user taught or oversees are included."
    return data
    pass


def subject_trend(scope, subject="", form=None):
    """Class average and pass rate for a subject per year, term and form, across all years."""
    subject = (subject or "").strip()
    if len(subject) < 2:
        return {"error": "Give a subject name."}

    qs = scope.all_sections().filter(course__name__icontains=subject)
    if form:
        qs = qs.filter(form__name__icontains=form)
    sections = list(qs)
    if not sections:
        return {"error": "No sections found for that subject that you can access."}

    grades, _ = _term_grades(scope, sections)
    by_section = {}
    for (section_id, _student_id), g in grades.items():
        by_section.setdefault(section_id, []).append(g)

    pass_marks = {}
    groups = {}
    for s in sections:
        vals = by_section.get(s.pk)
        if not vals:
            continue
        if s.form_id not in pass_marks:
            pass_marks[s.form_id] = get_pass_mark(scope.school, s.form)
        key = (s.course.name, s.form.name, s.academic_year.name, s.term_number)
        group = groups.setdefault(key, {"vals": [], "pass_mark": pass_marks[s.form_id]})
        group["vals"].extend(vals)

    rows = []
    for (subject_name, form_name, year_name, term), group in groups.items():
        vals = group["vals"]
        passed = sum(1 for v in vals if v >= group["pass_mark"])
        rows.append(
            {
                "subject": subject_name,
                "form": form_name,
                "academic_year": year_name,
                "term": term,
                "students_graded": len(vals),
                "class_average": _mean(vals),
                "pass_rate_pct": round(100 * passed / len(vals), 1),
            }
        )
    rows.sort(key=lambda r: (r["subject"], r["form"], r["academic_year"], r["term"]))
    limit = MAX_ROWS * 2
    return {"rows": rows[:limit], "truncated": len(rows) > limit, "note": PASS_MARK_NOTE}
    pass


def list_sections(scope, term=None, year=None):
    year_obj, error = scope.resolve_year(year)
    if error:
        return {"error": error}
    qs = scope.sections(year_obj)
    term = _int(term)
    if term:
        qs = qs.filter(term_number=term)
    rows = [
        {
            "section_id": s.pk,
            "subject": s.course.name,
            "form": s.form.name,
            "term": s.term_number,
            "teacher": s.teacher.get_full_name() if s.teacher else None,
        }
        for s in qs.order_by("form__order", "course__name", "term_number")[: MAX_ROWS * 2]
    ]
    return {"academic_year": year_obj.name, "count": len(rows), "sections": rows}
    pass


def section_summary(scope, section_id=None):
    section = scope.all_sections().filter(pk=_int(section_id)).first()
    if not section:
        return {"error": "No section with that ID that you can access."}

    grades, students = _term_grades(scope, [section])
    pass_mark = get_pass_mark(scope.school, section.form)

    rows = []
    for st in students.values():
        rows.append({"name": st.get_full_name(), "student_id": st.student_id, "term_grade": grades.get((section.pk, st.pk))})
    rows.sort(key=lambda r: (r["term_grade"] is None, r["term_grade"] or 0))

    graded = [r["term_grade"] for r in rows if r["term_grade"] is not None]
    return {
        "subject": section.course.name,
        "form": section.form.name,
        "academic_year": section.academic_year.name,
        "term": section.term_number,
        "teacher": section.teacher.get_full_name() if section.teacher else None,
        "pass_mark": pass_mark,
        "enrolled": len(rows),
        "graded": len(graded),
        "class_average": _mean(graded),
        "failing_count": sum(1 for g in graded if g < pass_mark),
        "students": rows,
    }
    pass


def failing_students(scope, form=None, subject=None, term=None, year=None):
    year_obj, error = scope.resolve_year(year)
    if error:
        return {"error": error}
    term = _int(term) or _latest_term(scope.school, year_obj)
    qs = scope.sections(year_obj).filter(term_number=term)
    if form:
        qs = qs.filter(form__name__icontains=form)
    if subject:
        qs = qs.filter(course__name__icontains=subject)
    sections = list(qs)
    section_by_id = {s.pk: s for s in sections}
    grades, students = _term_grades(scope, sections)

    pass_marks = {}
    rows = []
    for (section_id, student_id), grade in grades.items():
        section = section_by_id[section_id]
        if section.form_id not in pass_marks:
            pass_marks[section.form_id] = get_pass_mark(scope.school, section.form)
        pass_mark = pass_marks[section.form_id]
        if grade < pass_mark:
            st = students[student_id]
            rows.append(
                {
                    "name": st.get_full_name(),
                    "student_id": st.student_id,
                    "form": section.form.name,
                    "subject": section.course.name,
                    "term_grade": grade,
                    "pass_mark": pass_mark,
                }
            )
    rows.sort(key=lambda r: (r["form"], r["name"], r["subject"]))
    data = {"academic_year": year_obj.name, "term": term, "total": len(rows), "rows": rows[:MAX_ROWS], "truncated": len(rows) > MAX_ROWS}
    if year_obj != scope.year:
        data["note"] = PASS_MARK_NOTE
    return data
    pass


def at_risk_students(scope, form=None, band=None):
    if not scope.is_admin:
        return {"error": "At-risk scores are only available to administrators."}
    latest = AtRiskScore.objects.filter(school=scope.school).aggregate(m=Max("computed_on"))["m"]
    if not latest:
        return {"error": "No at-risk scores have been computed yet."}

    qs = AtRiskScore.objects.filter(school=scope.school, computed_on=latest).select_related("student__form")
    if band in ("low", "watch", "high"):
        qs = qs.filter(band=band)
    else:
        qs = qs.exclude(band="low")
    if form:
        qs = qs.filter(student__form__name__icontains=form)

    rows = [
        {
            "name": r.student.get_full_name(),
            "student_id": r.student.student_id,
            "form": r.student.form.name if r.student.form else None,
            "score": float(r.score),
            "band": r.band,
            "top_factors": r.top_factors,
        }
        for r in qs.order_by("-score")[:MAX_ROWS]
    ]
    return {"computed_on": str(latest), "count": qs.count(), "rows": rows}
    pass


def teacher_courses(scope, teacher=None, subject=None, form=None, year=None):
    """Who teaches what in one year, from section assignments. Visible to all staff."""
    year_obj, error = scope.resolve_year(year)
    if error:
        return {"error": error}

    qs = (
        Section.objects.filter(school=scope.school, academic_year=year_obj, teacher__isnull=False)
        .select_related("course", "form", "teacher")
        .order_by("course__name", "form__order", "term_number")
    )
    if subject:
        qs = qs.filter(course__name__icontains=subject)
    if form:
        qs = qs.filter(form__name__icontains=form)

    needle = (teacher or "").strip().lower()
    groups = {}
    for s in qs:
        name = s.teacher.get_full_name()
        if needle and needle not in name.lower():
            continue
        key = (s.teacher_id, s.course_id, s.form_id)
        row = groups.setdefault(key, {"teacher": name, "subject": s.course.name, "form": s.form.name, "terms": []})
        row["terms"].append(s.term_number)

    rows = sorted(groups.values(), key=lambda r: (r["teacher"], r["subject"], r["form"]))
    limit = MAX_ROWS * 2
    return {
        "academic_year": year_obj.name,
        "count": len(rows),
        "rows": rows[:limit],
        "truncated": len(rows) > limit,
    }
    pass


TOOL_FUNCS = {
    "find_students": find_students,
    "student_overview": student_overview,
    "student_history": student_history,
    "subject_trend": subject_trend,
    "list_sections": list_sections,
    "section_summary": section_summary,
    "failing_students": failing_students,
    "at_risk_students": at_risk_students,
    "teacher_courses": teacher_courses,
}

_YEAR_PROP = {
    "type": "string",
    "description": "Optional academic year name exactly as listed, e.g. '2025-2026'. Defaults to the current year.",
}

TOOL_SCHEMAS = [
    {
        "name": "find_students",
        "description": "Search students the user can access (any year) by name or student ID. Returns student_id, name, current form and homeroom.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Name, part of a name, or student ID."}},
            "required": ["query"],
        },
    },
    {
        "name": "student_overview",
        "description": "One student's detail for ONE academic year: form that year, status, term grade per subject per term, year average per subject, pass mark, merit and demerit totals, and (admins, current year only) latest at-risk score.",
        "input_schema": {
            "type": "object",
            "properties": {
                "student_id": {"type": "string", "description": "The school's student ID (from find_students)."},
                "year": _YEAR_PROP,
            },
            "required": ["student_id"],
        },
    },
    {
        "name": "student_history",
        "description": "One student across ALL years on record: form, overall average, each subject's year average, and merit/demerit totals per year. Use for a student's trend or year-to-year comparison.",
        "input_schema": {
            "type": "object",
            "properties": {"student_id": {"type": "string", "description": "The school's student ID (from find_students)."}},
            "required": ["student_id"],
        },
    },
    {
        "name": "subject_trend",
        "description": "Class average and pass rate for a subject per academic year, term and form, across ALL years. Use for subject or class trends and year-to-year comparisons.",
        "input_schema": {
            "type": "object",
            "properties": {
                "subject": {"type": "string", "description": "Subject name or part of it, e.g. 'Math'."},
                "form": {"type": "string", "description": "Optional form name, e.g. 'Form 3'."},
            },
            "required": ["subject"],
        },
    },
    {
        "name": "list_sections",
        "description": "Class sections (subject + form + term) in one academic year that the user can access grades for, with section_id and teacher.",
        "input_schema": {
            "type": "object",
            "properties": {
                "term": {"type": "integer", "description": "Optional term number (1-3)."},
                "year": _YEAR_PROP,
            },
        },
    },
    {
        "name": "section_summary",
        "description": "One section's class list (any year) with each student's term grade, class average, pass mark and failing count.",
        "input_schema": {
            "type": "object",
            "properties": {"section_id": {"type": "integer", "description": "From list_sections."}},
            "required": ["section_id"],
        },
    },
    {
        "name": "failing_students",
        "description": "Students whose term grade is below the pass mark in a subject, for one academic year. Defaults to the latest term of that year. Filter by form and/or subject.",
        "input_schema": {
            "type": "object",
            "properties": {
                "form": {"type": "string", "description": "Optional form name, e.g. 'Form 3'."},
                "subject": {"type": "string", "description": "Optional subject name or part of it, e.g. 'Math'."},
                "term": {"type": "integer", "description": "Optional term number (1-3)."},
                "year": _YEAR_PROP,
            },
        },
    },
    {
        "name": "at_risk_students",
        "description": "Admins only. Students from the latest at-risk calculation, highest risk first. Excludes 'low' unless a band is given. Current data only, no history.",
        "input_schema": {
            "type": "object",
            "properties": {
                "form": {"type": "string", "description": "Optional form name."},
                "band": {"type": "string", "enum": ["low", "watch", "high"], "description": "Optional risk band."},
            },
        },
    },
    {
        "name": "teacher_courses",
        "description": "Which teacher taught which subject, form and terms in one academic year. Filter by teacher name, subject and/or form. Use for any question about who teaches or taught what.",
        "input_schema": {
            "type": "object",
            "properties": {
                "teacher": {"type": "string", "description": "Optional teacher name or part of it."},
                "subject": {"type": "string", "description": "Optional subject name or part of it."},
                "form": {"type": "string", "description": "Optional form name, e.g. 'Form 2'."},
                "year": _YEAR_PROP,
            },
        },
    },
]


def run_tool(scope, name, args):
    """Run one tool and return its JSON string. Never raises."""
    fn = TOOL_FUNCS.get(name)
    if fn is None:
        result = {"error": f"Unknown tool: {name}"}
    else:
        try:
            result = fn(scope, **(args or {}))
        except TypeError:
            result = {"error": "Invalid arguments for this tool."}
        except Exception:
            logger.exception("Ask AI tool %s failed", name)
            result = {"error": "The lookup failed."}
    return json.dumps(result, default=str)
    pass