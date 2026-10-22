from collections import OrderedDict

from grades.term_grades import load_section_grades, load_term_weights, section_term_grade, weights_for
from scheduling.models import Enrolment

def _mean(values):
    vals = [v for v in values if v is not None]
    if not vals:
        return None
    return round(sum(vals) / len(vals), 1)
    pass


def _unique(items):
    seen = []
    for item in items:
        if item and item not in seen:
            seen.append(item)
    return seen
    pass


def _teacher_name(section):
    teacher = section.teacher
    if not teacher:
        return "No teacher"
    name = teacher.get_full_name() if hasattr(teacher, "get_full_name") else ""
    return name or str(teacher)
    pass


def _area_key(course):
    """Group key + label by subject area; courses with no area (or 'other') stay separate by course."""
    area = getattr(course, "subject_area", "") or ""
    if area and area != "other":
        return area, course.get_subject_area_display()
    return f"course_{course.pk}", course.name
    pass


def _term_grade(subj, term):
    return _mean([x["grade"] for x in subj["terms"].get(term, [])])
    pass


def _term_class(subj, term):
    return _mean([x["class_avg"] for x in subj["terms"].get(term, [])])
    pass


def _term_meta(subj, term):
    return _unique([f"{x['course']} · {x['teacher']}" for x in subj["terms"].get(term, [])])
    pass


def _year_avg(subj):
    return _mean([_term_grade(subj, t) for t in subj["terms"]])
    pass


def _year_meta(subj):
    return _unique([f"{x['course']} · {x['teacher']}" for t in sorted(subj["terms"]) for x in subj["terms"][t]])
    pass


def _year_teachers(subj):
    return _unique([x["teacher"] for t in sorted(subj["terms"]) for x in subj["terms"][t]])
    pass


def build_grade_history(school, student):
    """
    Per-year, per-subject-area grade history for one student across every academic year enrolled.
    Returns template-ready table rows plus a JSON-safe `chart` dict for Chart.js,
    including hover metadata (course + teacher) and class averages for the same sections.
    """
    empty = {
        "has_data": False,
        "year_names": [],
        "table_rows": [],
        "overall_cells": [],
        "subject_options": [],
        "chart": {
            "years": [],
            "overall": {
                "yearly": [],
                "yearly_meta": [],
                "term_labels": [],
                "term_values": [],
                "term_meta": [],
                "term_class": [],
            },
            "subjects": {},
        },
    }

    enrolments = list(
        Enrolment.objects.filter(student=student, section__school=school)
        .select_related("section__course", "section__academic_year", "section__teacher")
        .order_by(
            "section__academic_year__start_date",
            "section__academic_year__name",
            "section__term_number",
            "section__course__name",
        )
    )
    if not enrolments:
        return empty

    sections = [e.section for e in enrolments]
    section_pks = [s.pk for s in sections]

    # Evaluations + grade entries for these sections (this student + classmates) in two queries
    evals_by_section, gmap = load_section_grades(school, section_pks)

    # Coursework/exam weights per term from TermConfig, one query
    term_weights_map = load_term_weights(school, sections)

    # Classmates per section
    students_by_section = {}
    class_enrolments = Enrolment.objects.filter(section_id__in=section_pks, section__school=school).select_related("student")
    for ce in class_enrolments:
        students_by_section.setdefault(ce.section_id, []).append(ce.student)

    # Class average per section (shared term-grade logic, students with no grades skipped)
    class_avg_by_section = {}
    for sec in sections:
        evs = evals_by_section.get(sec.pk, [])
        class_avg_by_section[sec.pk] = _mean([section_term_grade(s, evs, gmap, weights_for(term_weights_map, sec)) for s in students_by_section.get(sec.pk, [])]) if evs else None

    # years[year_pk] = {"name", "terms": set, "subjects": {area_key: {"name", "terms": {term: [{grade, class_avg, course, teacher}]}}}}
    years = OrderedDict()
    for sec in sections:
        grade = section_term_grade(student, evals_by_section.get(sec.pk, []), gmap, weights_for(term_weights_map, sec))
        year = years.setdefault(
            sec.academic_year_id,
            {"name": sec.academic_year.name, "terms": set(), "subjects": {}},
        )
        key, label = _area_key(sec.course)
        subj = year["subjects"].setdefault(key, {"name": label, "terms": {}})
        if grade is not None:
            subj["terms"].setdefault(sec.term_number, []).append(
                {
                    "grade": grade,
                    "class_avg": class_avg_by_section.get(sec.pk),
                    "course": sec.course.name,
                    "teacher": _teacher_name(sec),
                }
            )
            year["terms"].add(sec.term_number)

    year_keys = list(years.keys())
    year_names = [years[k]["name"] for k in year_keys]

    # Subject areas with at least one grade, sorted by label
    subject_meta = {}
    for yk in year_keys:
        for key, subj in years[yk]["subjects"].items():
            if subj["terms"] and key not in subject_meta:
                subject_meta[key] = subj["name"]
    subject_meta = OrderedDict(sorted(subject_meta.items(), key=lambda kv: kv[1]))

    if not subject_meta:
        return empty

    # Overall yearly averages + hover meta
    overall_yearly = []
    overall_yearly_meta = []
    for yk in year_keys:
        avgs = []
        lines = []
        for key, name in subject_meta.items():
            subj = years[yk]["subjects"].get(key)
            if not subj or not subj["terms"]:
                continue
            avg = _year_avg(subj)
            if avg is None:
                continue
            avgs.append(avg)
            lines.append(f"{name}: {avg:.1f}% ({', '.join(_year_teachers(subj))})")
        overall_yearly.append(_mean(avgs))
        overall_yearly_meta.append(lines)

    # Overall term-by-term trend + hover meta + class average
    overall_term_labels = []
    overall_term_values = []
    overall_term_meta = []
    overall_term_class = []
    for yk in year_keys:
        year = years[yk]
        for t in sorted(year["terms"]):
            vals = []
            class_vals = []
            lines = []
            for key in subject_meta:
                subj = year["subjects"].get(key)
                if not subj or t not in subj["terms"]:
                    continue
                vals.append(_term_grade(subj, t))
                class_vals.append(_term_class(subj, t))
                for x in subj["terms"][t]:
                    lines.append(f"{x['course']} · {x['teacher']}: {x['grade']:.1f}%")
            overall_term_labels.append(f"{year['name']} T{t}")
            overall_term_values.append(_mean(vals))
            overall_term_class.append(_mean(class_vals))
            overall_term_meta.append(lines)

    # Per-subject-area series + hover meta + class average
    chart_subjects = {}
    table_rows = []
    for key, name in subject_meta.items():
        yearly = []
        yearly_meta = []
        cells = []
        term_labels = []
        term_values = []
        term_meta = []
        term_class = []
        for yk in year_keys:
            subj = years[yk]["subjects"].get(key)
            if not subj or not subj["terms"]:
                yearly.append(None)
                yearly_meta.append([])
                cells.append({"value": None, "title": ""})
                continue
            avg = _year_avg(subj)
            meta = _year_meta(subj)
            yearly.append(avg)
            yearly_meta.append(meta)
            cells.append({"value": avg, "title": "; ".join(meta)})
            for t in sorted(subj["terms"]):
                term_labels.append(f"{years[yk]['name']} T{t}")
                term_values.append(_term_grade(subj, t))
                term_class.append(_term_class(subj, t))
                term_meta.append(_term_meta(subj, t))

        chart_subjects[key] = {
            "name": name,
            "yearly": yearly,
            "yearly_meta": yearly_meta,
            "term_labels": term_labels,
            "term_values": term_values,
            "term_meta": term_meta,
            "term_class": term_class,
        }
        table_rows.append({"name": name, "cells": cells})

    return {
        "has_data": True,
        "year_names": year_names,
        "table_rows": table_rows,
        "overall_cells": overall_yearly,
        "subject_options": [{"key": key, "name": name} for key, name in subject_meta.items()],
        "chart": {
            "years": year_names,
            "overall": {
                "yearly": overall_yearly,
                "yearly_meta": overall_yearly_meta,
                "term_labels": overall_term_labels,
                "term_values": overall_term_values,
                "term_meta": overall_term_meta,
                "term_class": overall_term_class,
            },
            "subjects": chart_subjects,
        },
    }
    pass