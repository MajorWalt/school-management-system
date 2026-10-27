"""
Data and prompt for AI report card comments (subject comments, one per student per section).
Term grades come from grades.term_grades only.
Pass mark comes from the admin-managed analytics.PromotionCriteria for the section's form.
Only the student's first name and grade figures are sent to the API.
"""

from analytics.models import PromotionCriteria
from grades.term_grades import (
    combine_term_grade,
    load_section_grades,
    section_components,
    term_grades_for_section,
    term_weights,
)
from scheduling.models import Section

# Used only when the form has no PromotionCriteria row. Matches the PromotionCriteria model default.
DEFAULT_PASS_MARK = 55
COMMENT_MAX_TOKENS = 1024

SYSTEM_PROMPT = """You write subject-teacher comments for secondary school report cards in Dominica.

Rules:
- Maximum 2 sentences.
- Refer to the student by first name only. Avoid he/she pronouns; repeat the name or rephrase.
- Base every statement only on the data given. Do not mention behaviour, attendance, homework, effort or participation; no data on those is provided.
- Do not quote exact percentages and do not mention the class average directly. Describe performance in words (for example: excellent, solid, just below the pass mark, improved since last term).
- Note one strength or positive point. Where the term grade is below the pass mark, or the exam is clearly lower than coursework, name one clear area to work on.
- Professional, warm and honest tone suitable for parents. No exclamation marks, no emojis.
- Use British English spelling.
- Reply with the comment text only: no preamble, no quotation marks."""


def _fmt(value):
    """Percentage for the prompt, or 'not recorded'."""
    if value is None:
        return "not recorded"
    try:
        return f"{float(value):.1f}%"
    except (TypeError, ValueError):
        return "not recorded"
    pass


def get_pass_mark(school, form):
    """Pass mark (%) for a form from the admin-managed promotion criteria."""
    criteria = PromotionCriteria.objects.filter(school=school, form=form).first()
    return criteria.pass_mark if criteria else DEFAULT_PASS_MARK
    pass


def section_students(section):
    """Enrolled students in display order."""
    enrolments = section.enrolments.select_related("student").order_by("student__last_name", "student__first_name")
    return [e.student for e in enrolments]
    pass


def build_comment_inputs(school, section):
    """
    One dict per enrolled student:
    student, coursework, exam, has_exam, term_grade, class_average, previous_term_grade, pass_mark.
    """
    students = section_students(section)
    if not students:
        return []

    evals_by_section, grade_map = load_section_grades(school, [section.pk], [s.pk for s in students])
    evs = evals_by_section.get(section.pk, [])
    has_exam = any(e.is_final_exam for e in evs)
    weights = term_weights(school, section.academic_year_id, section.term_number)
    pass_mark = get_pass_mark(school, section.form)

    rows = []
    for student in students:
        cw, ex = section_components(student, evs, grade_map)
        rows.append(
            {
                "student": student,
                "coursework": cw,
                "exam": ex,
                "has_exam": has_exam,
                "term_grade": combine_term_grade(cw, ex, weights),
            }
        )

    graded = [r["term_grade"] for r in rows if r["term_grade"] is not None]
    class_average = round(sum(graded) / len(graded), 1) if graded else None

    previous = {}
    if section.term_number > 1:
        prev_section = Section.objects.filter(
            school=school,
            course=section.course,
            form=section.form,
            academic_year=section.academic_year,
            term_number=section.term_number - 1,
        ).first()
        if prev_section:
            previous = term_grades_for_section(school, prev_section, students)

    for r in rows:
        r["class_average"] = class_average
        r["previous_term_grade"] = previous.get(r["student"].pk)
        r["pass_mark"] = pass_mark

    return rows
    pass


def build_user_message(section, row):
    """Plain-text data block for one student."""
    exam_line = _fmt(row["exam"]) if row["has_exam"] else "no exam this term"
    if row["previous_term_grade"] is not None:
        previous_line = _fmt(row["previous_term_grade"])
    else:
        previous_line = "none (first term or no record)"

    lines = [
        f"Student first name: {row['student'].first_name}",
        f"Subject: {section.course.name}",
        f"Term: {section.term_number}",
        f"Coursework average: {_fmt(row['coursework'])}",
        f"Exam: {exam_line}",
        f"Term grade: {_fmt(row['term_grade'])}",
        f"Pass mark: {row['pass_mark']}%",
        f"Class average term grade: {_fmt(row['class_average'])}",
        f"Previous term grade in this subject: {previous_line}",
    ]
    return "\n".join(lines)
    pass