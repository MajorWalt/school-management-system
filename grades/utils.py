from decimal import Decimal
from .models import GradeEntry, GradeVisibilityRule


def compute_term_grade(enrolment):
    """
    Computes the term grade for an enrolment using TermConfig weights.
    Returns a dict: {coursework_avg, exam_mark, term_grade, percentage}
    """
    section      = enrolment.section
    academic_year = section.academic_year
    school       = section.school
    term_number  = section.term_number
    student_form = section.form

    # Get term config
    try:
        from scheduling.models import TermConfig, FormTermRule
        term_config = TermConfig.objects.get(
            academic_year=academic_year,
            term_number=term_number,
        )
    except TermConfig.DoesNotExist:
        return None

    # Check for form-level override
    form_rule = FormTermRule.objects.filter(
        academic_year=academic_year,
        form=student_form,
        term_number=term_number,
    ).first()

    entries         = GradeEntry.objects.filter(enrolment=enrolment)
    coursework_entries = entries.filter(is_final_exam=False)
    exam_entry      = entries.filter(is_final_exam=True).first()

    # Coursework average (weighted)
    coursework_avg = Decimal("0")
    total_weight   = sum(e.weight for e in coursework_entries)
    if total_weight > 0:
        coursework_avg = sum(
            (e.marks_earned / e.max_marks) * 100 * e.weight
            for e in coursework_entries
            if e.max_marks > 0
        ) / total_weight

    # Exam mark
    exam_mark = Decimal("0")
    if exam_entry and exam_entry.max_marks > 0:
        exam_mark = (exam_entry.marks_earned / exam_entry.max_marks) * 100

    # Compute term grade
    cw_weight   = Decimal(term_config.coursework_weight) / 100
    exam_weight = Decimal(term_config.exam_weight) / 100

    if not term_config.has_final_exam:
        term_grade = coursework_avg
    else:
        term_grade = (coursework_avg * cw_weight) + (exam_mark * exam_weight)

    return {
        "coursework_avg": round(coursework_avg, 2),
        "exam_mark":      round(exam_mark, 2),
        "term_grade":     round(term_grade, 2),
        "has_exam":       term_config.has_final_exam,
        "exam_label":     form_rule.exam_label if form_rule else "Final Exam",
        "cw_weight":      term_config.coursework_weight,
        "exam_weight":    term_config.exam_weight,
    }


def grades_visible_for_student(school, student):
    """
    Returns True if grades should be shown to this student in the portal.
    Per-student rule takes priority over school-wide rule.
    """
    # Per-student rule first
    student_rule = GradeVisibilityRule.objects.filter(
        school=school, student=student
    ).order_by("-updated_at").first()
    if student_rule:
        return student_rule.is_visible

    # Fall back to school-wide rule
    school_rule = GradeVisibilityRule.objects.filter(
        school=school, student__isnull=True
    ).order_by("-updated_at").first()
    if school_rule:
        return school_rule.is_visible

    return False  # hidden by default