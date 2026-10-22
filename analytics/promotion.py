
from collections import defaultdict

from attendance.utils import get_active_academic_year
from grades.term_grades import load_section_grades, load_term_weights, section_term_grade, weights_for
from scheduling.models import Course, Enrolment, Form
from students.models import Student

from .models import PromotionCriteria

AREA_LABELS = dict(Course.SUBJECT_AREA_CHOICES)


def _mean(values):
    vals = [v for v in values if v is not None]
    return round(sum(vals) / len(vals), 1) if vals else None
    pass


def evaluate_school(school, form_id=None, homerooms=None):
    """
    Returns {
      "year", "rows" (students not meeting criteria), "checked", "no_grades",
      "forms_without_criteria", "error"
    }
    homerooms: optional queryset to limit to (teacher view).
    """
    result = {"year": None, "rows": [], "checked": 0, "no_grades": 0, "forms_without_criteria": [], "error": ""}

    year = get_active_academic_year(school)
    if not year:
        result["error"] = "No active academic year."
        return result
    result["year"] = year

    criteria = {
        c.form_id: c
        for c in PromotionCriteria.objects.filter(school=school, active=True).select_related("form").prefetch_related("requirements")
    }
    result["forms_without_criteria"] = [f for f in Form.objects.filter(school=school).order_by("order", "name") if f.pk not in criteria]
    if not criteria:
        return result

    students_qs = Student.objects.filter(school=school, homeroom__isnull=False, form_id__in=list(criteria)).select_related("form", "homeroom")
    if form_id:
        students_qs = students_qs.filter(form_id=form_id)
    if homerooms is not None:
        students_qs = students_qs.filter(homeroom__in=homerooms)
    students = [s for s in students_qs.order_by("last_name", "first_name") if s.current_status() == "enrolled"]
    if not students:
        return result

    enrolments = list(
        Enrolment.objects.filter(student__in=students, section__school=school, section__academic_year=year).select_related("section", "section__course")
    )
    sections = {e.section_id: e.section for e in enrolments}
    evals_by_section, gmap = load_section_grades(school, list(sections), [s.pk for s in students])
    weights_map = load_term_weights(school, sections.values())
    by_id = {s.pk: s for s in students}

    # Weighted term grades per (student, course)
    course_terms = defaultdict(list)
    courses = {}
    for e in enrolments:
        sec = e.section
        evs = evals_by_section.get(sec.pk, [])
        if not evs:
            continue
        grade = section_term_grade(by_id[e.student_id], evs, gmap, weights_for(weights_map, sec))
        if grade is None:
            continue
        course_terms[(e.student_id, sec.course_id)].append(grade)
        courses[sec.course_id] = sec.course

    # Year average per (student, course) = equal-weight mean of its term grades
    course_avgs = defaultdict(dict)
    for (sid, cid), grades in course_terms.items():
        course_avgs[sid][cid] = _mean(grades)

    rows = []
    for s in students:
        c = criteria[s.form_id]
        avgs = course_avgs.get(s.pk, {})
        if not avgs:
            result["no_grades"] += 1
            continue
        result["checked"] += 1
        pass_mark = c.pass_mark

        area_grades = defaultdict(list)
        for cid, avg in avgs.items():
            area = courses[cid].subject_area
            if area:
                area_grades[area].append(avg)
        area_avg = {a: _mean(v) for a, v in area_grades.items()}

        counted = {cid: avg for cid, avg in avgs.items() if courses[cid].calc_average}
        overall = _mean(counted.values())
        failed = sorted(((courses[cid].name, avg) for cid, avg in counted.items() if avg < pass_mark), key=lambda x: x[1])

        unmet = []
        for req in c.requirements.all():
            areas = req.subject_areas or []
            parts = []
            passed = 0
            for a in areas:
                avg = area_avg.get(a)
                name = AREA_LABELS.get(a, a)
                if avg is None:
                    parts.append(f"{name}: no grades")
                else:
                    parts.append(f"{name}: {avg:.1f}%")
                    if avg >= pass_mark:
                        passed += 1
            if passed < req.min_to_pass:
                if len(areas) > 1:
                    need = f"needs {req.min_to_pass} of {len(areas)} at {pass_mark}%"
                else:
                    need = f"needs {pass_mark}%"
                unmet.append({"label": req.label, "detail": "; ".join(parts), "need": need})

        if c.min_overall_average is not None and (overall is None or overall < float(c.min_overall_average)):
            unmet.append(
                {
                    "label": "Overall average",
                    "detail": f"{overall:.1f}%" if overall is not None else "no grades",
                    "need": f"needs {c.min_overall_average}%",
                }
            )
        if c.max_failed_subjects is not None and len(failed) > c.max_failed_subjects:
            unmet.append(
                {
                    "label": "Subjects failed",
                    "detail": f"{len(failed)} below {pass_mark}%",
                    "need": f"no more than {c.max_failed_subjects}",
                }
            )

        if unmet:
            rows.append(
                {
                    "student": s,
                    "form": s.form,
                    "homeroom": s.homeroom,
                    "outcome": c.outcome,
                    "outcome_label": "May not graduate" if c.outcome == "graduation" else f"May repeat {s.form.name}",
                    "unmet": unmet,
                    "overall": overall,
                    "failed": failed,
                    "pass_mark": pass_mark,
                }
            )

    rows.sort(key=lambda r: (-len(r["unmet"]), r["overall"] if r["overall"] is not None else 0))
    result["rows"] = rows
    return result
    pass