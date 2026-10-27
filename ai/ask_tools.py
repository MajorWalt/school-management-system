"""
Read-only tools for Ask AI.
Every query is scoped to the current school and active academic year. Non-admins only see
sections they teach, plus their departments' sections if they are HODs. At-risk data is admin-only.
Teacher-to-course assignments (teacher_courses) are visible to all staff.
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
from scheduling.models import Enrolment, Section
from students.models import Student

from .comments import DEFAULT_PASS_MARK, get_pass_mark

logger = logging.getLogger(__name__)

MAX_ROWS = 60


class AskScope:
    """Who is asking and what they are allowed to see."""

    def __init__(self, user, school):
        self.user = user
        self.school = school
        self.is_admin = is_admin(user, school)
        self.staff = get_teacher_staff(user)
        self.hod_departments = get_hod_departments(self.staff)
        self.year = get_active_academic_year(school)
        self.current_term = self._current_term()
        pass

    def _current_term(self):
        """Latest term in the active year that has any evaluations."""
        if not self.year:
            return None
        latest = Evaluation.objects.filter(school=self.school, section__academic_year=self.year).aggregate(m=Max("section__term_number"))["m"]
        return latest or 1
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

    def sections(self):
        if not self.year:
            return Section.objects.none()
        qs = Section.objects.filter(school=self.school, academic_year=self.year).select_related("course", "form", "teacher")
        if self.is_admin:
            return qs
        if not self.staff:
            return qs.none()
        q = Q(teacher=self.staff)
        if self.hod_departments:
            q |= Q(course__department__in=self.hod_departments)
        return qs.filter(q)
        pass

    def students(self):
        qs = Student.objects.filter(school=self.school)
        if self.is_admin:
            return qs
        return qs.filter(enrolments__section__in=self.sections()).distinct()
        pass


def _int(value):
    try:
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None
    pass


def _term_grades(scope, sections, student_ids=None):
    """
    (grades, students) for the given sections.
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
            "form": s.form.name if s.form else None,
            "homeroom": s.homeroom.name if s.homeroom else None,
        }
        for s in qs[:15]
    ]
    return {"count": len(rows), "students": rows}
    pass


def student_overview(scope, student_id=""):
    student = scope.students().select_related("form", "homeroom").filter(student_id=str(student_id).strip()).first()
    if not student:
        return {"error": "No student with that ID that you can access."}

    sections = scope.sections().filter(enrolments__student=student).order_by("course__name", "term_number")
    grades, _ = _term_grades(scope, sections, [student.pk])

    subjects = {}
    for s in sections:
        subjects.setdefault(s.course.name, {})[f"term_{s.term_number}"] = grades.get((s.pk, student.pk))
    for terms in subjects.values():
        vals = [v for v in terms.values() if v is not None]
        terms["year_average"] = round(sum(vals) / len(vals), 1) if vals else None

    merits = MeritRecord.objects.filter(school=scope.school, student=student, academic_year=scope.year).aggregate(t=Sum("count"))["t"] or 0
    demerits = DemeritRecord.objects.filter(school=scope.school, student=student, academic_year=scope.year).aggregate(t=Sum("count"))["t"] or 0

    data = {
        "name": student.get_full_name(),
        "student_id": student.student_id,
        "form": student.form.name if student.form else None,
        "homeroom": student.homeroom.name if student.homeroom else None,
        "status": student.current_status_display(),
        "academic_year": scope.year.name if scope.year else None,
        "pass_mark": get_pass_mark(scope.school, student.form) if student.form else DEFAULT_PASS_MARK,
        "subjects": subjects,
        "merits_this_year": merits,
        "demerits_this_year": demerits,
    }
    if scope.is_admin:
        risk = AtRiskScore.objects.filter(school=scope.school, student=student).order_by("-computed_on").first()
        if risk:
            data["at_risk"] = {
                "score": float(risk.score),
                "band": risk.band,
                "computed_on": str(risk.computed_on),
                "top_factors": risk.top_factors,
            }
    else:
        data["note"] = "Only subjects in sections this user teaches or oversees are included."
    return data
    pass


def list_sections(scope, term=None):
    qs = scope.sections()
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
    return {"count": len(rows), "sections": rows}
    pass


def section_summary(scope, section_id=None):
    section = scope.sections().filter(pk=_int(section_id)).first()
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
        "term": section.term_number,
        "teacher": section.teacher.get_full_name() if section.teacher else None,
        "pass_mark": pass_mark,
        "enrolled": len(rows),
        "graded": len(graded),
        "class_average": round(sum(graded) / len(graded), 1) if graded else None,
        "failing_count": sum(1 for g in graded if g < pass_mark),
        "students": rows,
    }
    pass


def failing_students(scope, form=None, subject=None, term=None):
    term = _int(term) or scope.current_term
    qs = scope.sections().filter(term_number=term)
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
    return {"term": term, "total": len(rows), "rows": rows[:MAX_ROWS], "truncated": len(rows) > MAX_ROWS}
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


def teacher_courses(scope, teacher=None, subject=None, form=None):
    """Who teaches what in the active year, from section assignments. Visible to all staff."""
    if not scope.year:
        return {"error": "No active academic year is set."}

    qs = (
        Section.objects.filter(school=scope.school, academic_year=scope.year, teacher__isnull=False)
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
        "academic_year": scope.year.name,
        "count": len(rows),
        "rows": rows[:limit],
        "truncated": len(rows) > limit,
    }
    pass


TOOL_FUNCS = {
    "find_students": find_students,
    "student_overview": student_overview,
    "list_sections": list_sections,
    "section_summary": section_summary,
    "failing_students": failing_students,
    "at_risk_students": at_risk_students,
    "teacher_courses": teacher_courses,
}

TOOL_SCHEMAS = [
    {
        "name": "find_students",
        "description": "Search students the user can access by name or student ID. Returns student_id, name, form and homeroom.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Name, part of a name, or student ID."}},
            "required": ["query"],
        },
    },
    {
        "name": "student_overview",
        "description": "One student's profile for the current academic year: form, homeroom, status, term grade per subject per term, year average per subject, pass mark, merit and demerit totals, and (admins only) latest at-risk score.",
        "input_schema": {
            "type": "object",
            "properties": {"student_id": {"type": "string", "description": "The school's student ID (from find_students)."}},
            "required": ["student_id"],
        },
    },
    {
        "name": "list_sections",
        "description": "Class sections (subject + form + term) in the current academic year that the user can access grades for, with section_id and teacher.",
        "input_schema": {
            "type": "object",
            "properties": {"term": {"type": "integer", "description": "Optional term number (1-3)."}},
        },
    },
    {
        "name": "section_summary",
        "description": "One section's class list with each student's term grade, class average, pass mark and failing count.",
        "input_schema": {
            "type": "object",
            "properties": {"section_id": {"type": "integer", "description": "From list_sections."}},
            "required": ["section_id"],
        },
    },
    {
        "name": "failing_students",
        "description": "Students whose term grade is below the pass mark in a subject. Defaults to the current term. Filter by form name and/or subject name.",
        "input_schema": {
            "type": "object",
            "properties": {
                "form": {"type": "string", "description": "Optional form name, e.g. 'Form 3'."},
                "subject": {"type": "string", "description": "Optional subject name or part of it, e.g. 'Math'."},
                "term": {"type": "integer", "description": "Optional term number (1-3)."},
            },
        },
    },
    {
        "name": "at_risk_students",
        "description": "Admins only. Students from the latest at-risk calculation, highest risk first. Excludes 'low' unless a band is given.",
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
        "description": "Which teacher teaches which subject, form and terms in the current academic year. Filter by teacher name, subject and/or form. Use for any question about who teaches what.",
        "input_schema": {
            "type": "object",
            "properties": {
                "teacher": {"type": "string", "description": "Optional teacher name or part of it."},
                "subject": {"type": "string", "description": "Optional subject name or part of it."},
                "form": {"type": "string", "description": "Optional form name, e.g. 'Form 2'."},
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