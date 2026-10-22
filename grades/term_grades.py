"""
Every feature that shows or uses a term grade (report card page, report card
PDF, grade history, AtRiskScore, AI comments) must go through this module.
"""

from grades.models import Evaluation, GradeEntry
from grades.utils import compute_student_average
from scheduling.models import TermConfig


# Used only when a term has no TermConfig row. Matches the TermConfig model defaults.
DEFAULT_WEIGHTS = (60, 40)  # (coursework %, exam %)


def _as_float(v):
    if v is None or v == "" or v == "-":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None
    pass


# -- Weights -------------------------------------------------------------------


def load_term_weights(school, sections):
    """
    Bulk loader: one query for every term the given sections belong to.
    Returns {(academic_year_id, term_number): (coursework_weight, exam_weight)}.
    """
    year_ids = {s.academic_year_id for s in sections}
    if not year_ids:
        return {}
    configs = TermConfig.objects.filter(academic_year__school=school, academic_year_id__in=year_ids)
    return {(tc.academic_year_id, tc.term_number): (tc.coursework_weight, tc.exam_weight) for tc in configs}
    pass


def weights_for(weights_map, section):
    """(coursework_weight, exam_weight) for a section from a load_term_weights() map."""
    return weights_map.get((section.academic_year_id, section.term_number), DEFAULT_WEIGHTS)
    pass


def term_weights(school, academic_year_id, term_number):
    """(coursework_weight, exam_weight) for one term (one-off lookups)."""
    tc = TermConfig.objects.filter(academic_year__school=school, academic_year_id=academic_year_id, term_number=term_number).first()
    return (tc.coursework_weight, tc.exam_weight) if tc else DEFAULT_WEIGHTS
    pass


# -- Components ----------------------------------------------------------------


def split_evaluations(evaluations):
    """(coursework_evaluations, final_exam_evaluations)."""
    coursework = [e for e in evaluations if not e.is_final_exam]
    exams = [e for e in evaluations if e.is_final_exam]
    return coursework, exams
    pass


def section_components(student, evaluations, grade_map):
    """
    (coursework_avg, exam_avg) for one student in one section, exactly as
    compute_student_average returns them. None where a component has no
    evaluations or no marks.
    """
    coursework, exams = split_evaluations(evaluations)
    cw = compute_student_average(student, coursework, grade_map) if coursework else None
    ex = compute_student_average(student, exams, grade_map) if exams else None
    return cw, ex
    pass


# -- Term grade ----------------------------------------------------------------


def combine_term_grade(coursework, exam, weights):
    """
    Weighted term grade from the two components, rounded to 1 dp.
    weights = (coursework_weight, exam_weight). Missing or zero-weight
    components are dropped and the rest re-normalised. None if nothing is left.
    """
    cw_weight, ex_weight = weights
    parts = []
    cw = _as_float(coursework)
    ex = _as_float(exam)
    if cw is not None and cw_weight:
        parts.append((cw, cw_weight))
    if ex is not None and ex_weight:
        parts.append((ex, ex_weight))
    if not parts:
        return None
    total_weight = sum(w for _, w in parts)
    return round(sum(v * w for v, w in parts) / total_weight, 1)
    pass


def section_term_grade(student, evaluations, grade_map, weights):
    """Term grade for one student in one section from pre-loaded evaluations, grade map and weights."""
    cw, ex = section_components(student, evaluations, grade_map)
    return combine_term_grade(cw, ex, weights)
    pass


# -- Loaders -------------------------------------------------------------------


def load_section_grades(school, section_ids, student_ids=None):
    """
    Bulk loader: two queries total, regardless of how many sections or students.
    Returns (evals_by_section, grade_map) where
      evals_by_section = {section_id: [Evaluation, ...]}
      grade_map        = {(evaluation_id, student_id): GradeEntry}
    """
    evals = list(Evaluation.objects.filter(school=school, section_id__in=section_ids))
    evals_by_section = {}
    for ev in evals:
        evals_by_section.setdefault(ev.section_id, []).append(ev)

    entries = GradeEntry.objects.filter(school=school, evaluation__in=evals)
    if student_ids is not None:
        entries = entries.filter(student_id__in=student_ids)
    grade_map = {(e.evaluation_id, e.student_id): e for e in entries}
    return evals_by_section, grade_map
    pass


def term_grade(school, student, section):
    """Term grade for one student in one section (one-off lookups)."""
    evals_by_section, grade_map = load_section_grades(school, [section.pk], [student.pk])
    weights = term_weights(school, section.academic_year_id, section.term_number)
    return section_term_grade(student, evals_by_section.get(section.pk, []), grade_map, weights)
    pass


def term_grades_for_section(school, section, students):
    """{student_id: term_grade} for a whole class, in three queries."""
    students = list(students)
    evals_by_section, grade_map = load_section_grades(school, [section.pk], [s.pk for s in students])
    weights = term_weights(school, section.academic_year_id, section.term_number)
    evs = evals_by_section.get(section.pk, [])
    return {s.pk: section_term_grade(s, evs, grade_map, weights) for s in students}
    pass