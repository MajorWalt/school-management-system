import datetime
import json
import logging
import re

from django.contrib.auth import get_user_model
from django.db.models import Max, Q, Sum
from django.utils import timezone

from accounts.utils import is_admin
from analytics.models import AtRiskScore
from attendance.utils import get_active_academic_year
from core.models import ActivityLog
from grades.models import Evaluation
from grades.term_grades import load_section_grades, load_term_weights, section_term_grade, weights_for
from grades.views import get_hod_departments, get_teacher_staff
from merits.models import DemeritRecord, MeritRecord
from scheduling.models import AcademicYear, Course, Enrolment, Form, Section
from students.models import Student

from .comments import DEFAULT_PASS_MARK, get_pass_mark

logger = logging.getLogger(__name__)

MAX_ROWS = 60
PASS_MARK_NOTE = "Pass marks are the current per-form settings, applied to every year."
ACTIVITY_DEFAULT_LIMIT = 25
ORDINAL_WORDS = {
    "first": 1,
    "1st": 1,
    "second": 2,
    "2nd": 2,
    "third": 3,
    "3rd": 3,
    "fourth": 4,
    "4th": 4,
    "fifth": 5,
    "5th": 5,
    "sixth": 6,
    "6th": 6,
}


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


def _bool(value):
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "y")
    return bool(value)
    pass


def _date(value):
    if value in (None, ""):
        return None
    try:
        return datetime.date.fromisoformat(str(value).strip()[:10])
    except ValueError:
        return None
    pass


def _clamp_limit(value, default):
    n = _int(value) or default
    return max(1, min(n, MAX_ROWS))
    pass


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
        self._forms = None
        self._courses = None
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

    @property
    def forms(self):
        if self._forms is None:
            self._forms = list(Form.objects.filter(school=self.school).order_by("order", "name"))
        return self._forms
        pass

    @property
    def courses(self):
        if self._courses is None:
            self._courses = list(Course.objects.filter(school=self.school).order_by("name"))
        return self._courses
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

    def resolve_form(self, name):
        """(Form, error). Exact name, then a single partial match, then a single form with that number ('5', '5th', 'fifth')."""
        wanted = str(name or "").strip()
        lower = wanted.lower()
        exact = [f for f in self.forms if f.name.lower() == lower]
        if len(exact) == 1:
            return exact[0], None
        partial = [f for f in self.forms if lower in f.name.lower()]
        if len(partial) == 1:
            return partial[0], None
        numbers = [str(ORDINAL_WORDS[w]) for w in re.findall(r"[a-z0-9]+", lower) if w in ORDINAL_WORDS]
        if not numbers:
            numbers = re.findall(r"\d+", wanted)
        if len(numbers) == 1:
            pattern = re.compile(rf"(?<!\d){numbers[0]}(?!\d)")
            by_number = [f for f in self.forms if pattern.search(f.name)]
            if len(by_number) == 1:
                return by_number[0], None
        on_record = ", ".join(f.name for f in self.forms) or "none"
        return None, f"No single form matches '{wanted}'. Forms on record: {on_record}."
        pass

    def resolve_subject(self, name):
        """
        (list of Course, error).
        Exact course name, then a subject area name, then partial course-name matches that all share one subject area.
        Partial matches spanning different subjects are ambiguous and return an error listing them.
        """
        wanted = str(name or "").strip()
        lower = wanted.lower()
        if len(lower) < 2:
            return [], "Subject name is too short."

        exact = [c for c in self.courses if c.name.lower() == lower]
        if exact:
            return exact, None

        area_codes = {code for code, label in Course.SUBJECT_AREA_CHOICES if lower in (code.lower(), label.lower())}
        if area_codes:
            by_area = [c for c in self.courses if c.subject_area in area_codes]
            if by_area:
                return by_area, None

        partial = [c for c in self.courses if lower in c.name.lower()]
        if not partial:
            stripped = re.sub(r"\d+", "", lower).strip()
            if stripped and stripped != lower and len(stripped) >= 2:
                partial = [c for c in self.courses if stripped in c.name.lower()]
        if not partial:
            return [], f"No subject matches '{wanted}'."

        groups = {c.subject_area if c.subject_area and c.subject_area != "other" else f"course_{c.pk}" for c in partial}
        if len(groups) == 1:
            return partial, None
        names = ", ".join(sorted(c.name for c in partial)[:15])
        return [], f"'{wanted}' matches several different subjects: {names}. Ask which one is meant, or use the exact name."
        pass

    def filter_sections(self, qs, form=None, subject=None, term=None):
        """
        Apply form/subject/term filters to a Section queryset.
        Returns (qs, matched, error); matched names the form and subjects actually used.
        """
        matched = {}
        if form not in (None, ""):
            form_obj, error = self.resolve_form(form)
            if error:
                return qs.none(), matched, error
            qs = qs.filter(form=form_obj)
            matched["form_matched"] = form_obj.name
        if subject not in (None, ""):
            courses, error = self.resolve_subject(subject)
            if error:
                return qs.none(), matched, error
            qs = qs.filter(course__in=courses)
        term = _int(term)
        if term:
            qs = qs.filter(term_number=term)
        if subject not in (None, ""):
            matched["subjects_matched"] = sorted(set(qs.values_list("course__name", flat=True)))
        return qs, matched, None
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


def _term_grades(scope, sections, student_ids=None):
    """
    (grades, students) for the given sections (any mix of years).
    grades   = {(section_id, student_id): term_grade}  (only graded students)
    students = {student_id: Student}                   (every enrolled student)
    """
    sections = [s for s in sections if s.school_id == scope.school.pk]
    if not sections:
        return {}, {}
    evals_by_section, grade_map = load_section_grades(scope.school, [s.pk for s in sections], student_ids)
    weights_map = load_term_weights(scope.school, sections)
    section_by_id = {s.pk: s for s in sections}

    enrolments = Enrolment.objects.filter(section__in=sections, section__school=scope.school, student__school=scope.school).select_related(
        "student", "student__form"
    )
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


def _user_label(user):
    if user is None:
        return "System"
    full = user.get_full_name() if hasattr(user, "get_full_name") else ""
    return full or str(user)
    pass


# -- Registry ------------------------------------------------------------------

_TOOLS = {}

_YEAR_PROP = {
    "type": "string",
    "description": "Optional academic year name exactly as listed, e.g. '2025-2026'. Defaults to the current year.",
}
_FORM_PROP = {"type": "string", "description": "Optional form name, e.g. 'Form 5'."}
_SUBJECT_PROP = {"type": "string", "description": "Optional subject name or part of it, e.g. 'Math'."}
_TERM_PROP = {"type": "integer", "description": "Optional term number (1-3)."}


def tool(name, description, properties=None, required=None, admin_only=False):
    """Register a tool function with its schema and access rule."""

    def decorator(fn):
        schema = {"type": "object", "properties": properties or {}}
        if required:
            schema["required"] = list(required)
        _TOOLS[name] = {
            "fn": fn,
            "admin_only": admin_only,
            "schema": {"name": name, "description": description, "input_schema": schema},
        }
        return fn
        pass

    return decorator
    pass


# -- Tools ---------------------------------------------------------------------


@tool(
    "find_students",
    "Search students the user can access (any year) by name or student ID. Returns student_id, name, current form and homeroom.",
    {"query": {"type": "string", "description": "Name, part of a name, or student ID."}},
    required=["query"],
)
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


@tool(
    "student_overview",
    "One student's detail for ONE academic year: form that year, status, term grade per subject per term, year average per subject, pass mark, merit and demerit totals, and (admins, current year only) latest at-risk score.",
    {
        "student_id": {"type": "string", "description": "The school's student ID (from find_students)."},
        "year": _YEAR_PROP,
    },
    required=["student_id"],
)
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


@tool(
    "student_history",
    "One student across ALL years on record: form, overall average, each subject's year average, and merit/demerit totals per year. Use for a student's trend or year-to-year comparison.",
    {"student_id": {"type": "string", "description": "The school's student ID (from find_students)."}},
    required=["student_id"],
)
def student_history(scope, student_id=""):
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


@tool(
    "subject_trend",
    "Class average and pass rate for a subject per academic year, term and form, across ALL years. Use for subject or class trends and year-to-year comparisons.",
    {
        "subject": {"type": "string", "description": "Subject name or part of it, e.g. 'Math'."},
        "form": _FORM_PROP,
    },
    required=["subject"],
)
def subject_trend(scope, subject="", form=None):
    if not (subject or "").strip():
        return {"error": "Give a subject name."}

    qs, matched, error = scope.filter_sections(scope.all_sections(), form=form, subject=subject)
    if error:
        return {"error": error}
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
    data = {**matched, "rows": rows[:limit], "truncated": len(rows) > limit, "note": PASS_MARK_NOTE}
    return data
    pass


@tool(
    "list_sections",
    "Class sections (subject + form + term) in one academic year that the user can access grades for, with section_id and teacher. Filter by form, subject and/or term; if 'truncated' is true, filter further.",
    {
        "form": _FORM_PROP,
        "subject": _SUBJECT_PROP,
        "term": _TERM_PROP,
        "year": _YEAR_PROP,
    },
)
def list_sections(scope, term=None, year=None, form=None, subject=None):
    year_obj, error = scope.resolve_year(year)
    if error:
        return {"error": error}
    qs, matched, error = scope.filter_sections(scope.sections(year_obj), form=form, subject=subject, term=term)
    if error:
        return {"error": error}
    total = qs.count()
    limit = MAX_ROWS * 2
    rows = [
        {
            "section_id": s.pk,
            "subject": s.course.name,
            "form": s.form.name,
            "term": s.term_number,
            "teacher": s.teacher.get_full_name() if s.teacher else None,
        }
        for s in qs.order_by("form__order", "course__name", "term_number")[:limit]
    ]
    data = {"academic_year": year_obj.name, **matched, "total": total, "count": len(rows), "truncated": total > limit, "sections": rows}
    if total > limit:
        data["note"] = "List cut off. Filter by form, subject and/or term to see the rest."
    return data
    pass


@tool(
    "section_summary",
    "One section's class list (any year) with each student's term grade, class average, pass mark and failing count.",
    {"section_id": {"type": "integer", "description": "From list_sections."}},
    required=["section_id"],
)
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


@tool(
    "rank_students",
    "Rank individual students by average, combining every class/homeroom of a form. With a subject: ranks by that subject's grade (e.g. lowest in Form 5 Technical Drawing). Without a subject: ranks by overall average across subjects (e.g. top 3 in Form 5). One term (default latest) or the whole year. Use for any 'top', 'best', 'lowest', 'weakest' or ranking question.",
    {
        "form": {"type": "string", "description": "Form name, e.g. 'Form 5'."},
        "subject": _SUBJECT_PROP,
        "term": {"type": "integer", "description": "Optional term number (1-3). Defaults to the latest term with grades."},
        "whole_year": {"type": "boolean", "description": "True to rank by the year average (mean of terms) instead of one term."},
        "order": {"type": "string", "enum": ["highest", "lowest"], "description": "Highest first or lowest first. Default lowest."},
        "limit": {"type": "integer", "description": "How many students to return (default 10, max 60)."},
        "year": _YEAR_PROP,
    },
)
def rank_students(scope, form=None, subject=None, term=None, year=None, whole_year=False, order="lowest", limit=None):
    """
    With a subject: the student's grade in that subject. Without: overall average of subjects that count toward the average.
    One term (default latest) or the whole year (mean of term grades per subject).
    """
    if not form and not subject:
        return {"error": "Give a form and/or a subject."}
    year_obj, error = scope.resolve_year(year)
    if error:
        return {"error": error}

    whole_year = _bool(whole_year)
    term_num = None if whole_year else (_int(term) or _latest_term(scope.school, year_obj))
    qs, matched, error = scope.filter_sections(scope.sections(year_obj), form=form, subject=subject, term=term_num)
    if error:
        return {"error": error}
    sections = list(qs)
    if not sections:
        return {"error": "No sections found for that form/subject that you can access."}

    section_by_id = {s.pk: s for s in sections}
    grades, students = _term_grades(scope, sections)

    per_student = {}
    for (section_id, student_id), g in grades.items():
        s = section_by_id[section_id]
        if not subject and not s.course.calc_average:
            continue
        entry = per_student.setdefault(student_id, {"subjects": {}, "forms": {}})
        entry["subjects"].setdefault(s.course.name, []).append(g)
        entry["forms"][s.form_id] = s.form

    pass_marks = {}
    rows = []
    for student_id, entry in per_student.items():
        subject_avgs = {name: _mean(vals) for name, vals in entry["subjects"].items()}
        average = _mean(subject_avgs.values())
        if average is None:
            continue
        form_objs = list(entry["forms"].values())
        for f in form_objs:
            if f.pk not in pass_marks:
                pass_marks[f.pk] = get_pass_mark(scope.school, f)
        pass_mark = pass_marks[form_objs[0].pk] if form_objs else DEFAULT_PASS_MARK
        st = students[student_id]
        rows.append(
            {
                "name": st.get_full_name(),
                "student_id": st.student_id,
                "form": ", ".join(sorted(f.name for f in form_objs)),
                "average": average,
                "subjects_graded": len(subject_avgs),
                "subjects_below_pass": sum(1 for v in subject_avgs.values() if v is not None and v < pass_mark),
                "subject_averages": subject_avgs,
            }
        )

    highest = str(order or "").strip().lower() in ("highest", "top", "desc", "best")
    rows.sort(key=lambda r: (-r["average"] if highest else r["average"], r["name"]))
    for i, r in enumerate(rows, start=1):
        r["rank"] = i
    limit = _clamp_limit(limit, 10)

    data = {
        "academic_year": year_obj.name,
        **matched,
        "term": "whole year" if whole_year else term_num,
        "basis": "grade in the matched subject(s)" if subject else "overall average of subjects that count toward the average",
        "order": "highest first" if highest else "lowest first",
        "students_ranked": len(rows),
        "rows": rows[:limit],
    }
    if not scope.is_admin:
        data["note"] = "Only sections this user taught or oversees are included."
    elif year_obj != scope.year:
        data["note"] = PASS_MARK_NOTE
    return data
    pass


@tool(
    "failing_students",
    "Students whose term grade is below the pass mark in a subject, for one academic year. Defaults to the latest term of that year. Filter by form and/or subject.",
    {
        "form": _FORM_PROP,
        "subject": _SUBJECT_PROP,
        "term": _TERM_PROP,
        "year": _YEAR_PROP,
    },
)
def failing_students(scope, form=None, subject=None, term=None, year=None):
    year_obj, error = scope.resolve_year(year)
    if error:
        return {"error": error}
    term = _int(term) or _latest_term(scope.school, year_obj)
    qs, matched, error = scope.filter_sections(scope.sections(year_obj), form=form, subject=subject, term=term)
    if error:
        return {"error": error}
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
    data = {
        "academic_year": year_obj.name,
        **matched,
        "term": term,
        "total": len(rows),
        "rows": rows[:MAX_ROWS],
        "truncated": len(rows) > MAX_ROWS,
    }
    if year_obj != scope.year:
        data["note"] = PASS_MARK_NOTE
    return data
    pass


@tool(
    "at_risk_students",
    "Admins only. Students from the latest at-risk calculation, highest risk first. Excludes 'low' unless a band is given. Current data only, no history.",
    {
        "form": _FORM_PROP,
        "band": {"type": "string", "enum": ["low", "watch", "high"], "description": "Optional risk band."},
    },
    admin_only=True,
)
def at_risk_students(scope, form=None, band=None):
    latest = AtRiskScore.objects.filter(school=scope.school).aggregate(m=Max("computed_on"))["m"]
    if not latest:
        return {"error": "No at-risk scores have been computed yet."}

    qs = AtRiskScore.objects.filter(school=scope.school, computed_on=latest).select_related("student__form")
    if band in ("low", "watch", "high"):
        qs = qs.filter(band=band)
    else:
        qs = qs.exclude(band="low")
    matched = {}
    if form:
        form_obj, error = scope.resolve_form(form)
        if error:
            return {"error": error}
        qs = qs.filter(student__form=form_obj)
        matched["form_matched"] = form_obj.name

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
    return {"computed_on": str(latest), **matched, "count": qs.count(), "rows": rows}
    pass


@tool(
    "teacher_courses",
    "Which teacher taught which subject, form and terms in one academic year. Filter by teacher name, subject and/or form. Use for any question about who teaches or taught what.",
    {
        "teacher": {"type": "string", "description": "Optional teacher name or part of it."},
        "subject": _SUBJECT_PROP,
        "form": _FORM_PROP,
        "year": _YEAR_PROP,
    },
)
def teacher_courses(scope, teacher=None, subject=None, form=None, year=None):
    """Visible to all staff, so not role-filtered."""
    year_obj, error = scope.resolve_year(year)
    if error:
        return {"error": error}

    base = Section.objects.filter(school=scope.school, academic_year=year_obj, teacher__isnull=False).select_related("course", "form", "teacher")
    qs, matched, error = scope.filter_sections(base, form=form, subject=subject)
    if error:
        return {"error": error}

    needle = (teacher or "").strip().lower()
    groups = {}
    for s in qs.order_by("course__name", "form__order", "term_number"):
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
        **matched,
        "count": len(rows),
        "rows": rows[:limit],
        "truncated": len(rows) > limit,
    }
    pass


@tool(
    "activity_log",
    "Admins only. The school's activity log (logins, grades saved, evaluations, attendance, merits, behaviour, student/staff changes, etc.), newest first. Filter by user, action, text in the description, and date range. Returns total_matching for counts.",
    {
        "user": {"type": "string", "description": "Optional user name or email, or part of it."},
        "action": {"type": "string", "enum": [code for code, _label in ActivityLog.ACTION_CHOICES], "description": "Optional action type."},
        "search": {"type": "string", "description": "Optional text to find in the description, e.g. a section or student name."},
        "days": {"type": "integer", "description": "Optional: only the last N days."},
        "date_from": {"type": "string", "description": "Optional start date, YYYY-MM-DD."},
        "date_to": {"type": "string", "description": "Optional end date, YYYY-MM-DD."},
        "limit": {"type": "integer", "description": "How many entries to return (default 25, max 60)."},
    },
    admin_only=True,
)
def activity_log(scope, user=None, action=None, search=None, days=None, date_from=None, date_to=None, limit=None):
    qs = ActivityLog.objects.filter(school=scope.school).select_related("user")

    if action:
        action = str(action).strip()
        if action not in dict(ActivityLog.ACTION_CHOICES):
            return {"error": f"Unknown action '{action}'."}
        qs = qs.filter(action=action)

    needle = (user or "").strip()
    if needle:
        field_names = {f.name for f in get_user_model()._meta.get_fields()}
        user_q = Q()
        for part in needle.split():
            part_q = Q()
            for field in ("first_name", "last_name", "username", "email"):
                if field in field_names:
                    part_q |= Q(**{f"user__{field}__icontains": part})
            user_q &= part_q
        qs = qs.filter(user_q)

    if search:
        qs = qs.filter(description__icontains=str(search).strip())

    days = _int(days)
    if days:
        qs = qs.filter(created_at__gte=timezone.now() - datetime.timedelta(days=days))
    start = _date(date_from)
    if start:
        qs = qs.filter(created_at__date__gte=start)
    end = _date(date_to)
    if end:
        qs = qs.filter(created_at__date__lte=end)

    total = qs.count()
    limit = _clamp_limit(limit, ACTIVITY_DEFAULT_LIMIT)
    rows = [
        {
            "when": timezone.localtime(log.created_at).strftime("%Y-%m-%d %H:%M"),
            "user": _user_label(log.user),
            "action": log.get_action_display(),
            "description": log.description,
        }
        for log in qs.order_by("-created_at")[:limit]
    ]
    return {"total_matching": total, "count": len(rows), "truncated": total > limit, "rows": rows}
    pass


# -- Public API ----------------------------------------------------------------

TOOL_FUNCS = {name: entry["fn"] for name, entry in _TOOLS.items()}
TOOL_SCHEMAS = [entry["schema"] for entry in _TOOLS.values()]


def schemas_for(scope):
    """Tool schemas this user may call. Pass these to the model instead of TOOL_SCHEMAS."""
    return [entry["schema"] for entry in _TOOLS.values() if scope.is_admin or not entry["admin_only"]]
    pass


def run_tool(scope, name, args):
    """Run one tool and return its JSON string. Never raises."""
    entry = _TOOLS.get(name)
    if entry is None:
        result = {"error": f"Unknown tool: {name}"}
    elif entry["admin_only"] and not scope.is_admin:
        result = {"error": "This lookup is only available to administrators."}
    else:
        try:
            result = entry["fn"](scope, **(args or {}))
        except TypeError:
            result = {"error": "Invalid arguments for this tool."}
        except Exception:
            logger.exception("Ask AI tool %s failed", name)
            result = {"error": "The lookup failed."}
    return json.dumps(result, default=str)
    pass