"""Utility functions for the scheduling app."""


def get_placement_for_year(student, academic_year):
    """
    Get the YearPlacement record for a student in a given academic year.

    Args:
        student: A students.Student instance
        academic_year: A scheduling.AcademicYear instance

    Returns:
        A scheduling.YearPlacement instance, or None if not found
    """
    from scheduling.models import YearPlacement

    return YearPlacement.objects.filter(student=student, academic_year=academic_year).first()


def get_homeroom_for_year(student, academic_year):
    """
    Get the homeroom a student was assigned to for a given academic year via YearPlacement.
    Falls back to student.homeroom if no placement row exists yet.

    Important: Only returns homeroom if outcome is 'continuing' (students who exited have null homeroom).

    Args:
        student: A students.Student instance
        academic_year: A scheduling.AcademicYear instance

    Returns:
        A scheduling.Homeroom instance, or None if not set or if student exited
    """
    placement = get_placement_for_year(student, academic_year)
    if placement:
        return placement.homeroom

    # Fallback to current student.homeroom if no placement exists yet
    return student.homeroom


def get_form_for_year(student, academic_year):
    """
    Get the form/class a student was assigned to for a given academic year via YearPlacement.
    Falls back to student.form if no placement row exists yet.

    Important: Only returns form if outcome is 'continuing' (students who exited have null form).

    Args:
        student: A students.Student instance
        academic_year: A scheduling.AcademicYear instance

    Returns:
        A scheduling.Form instance, or None if not set or if student exited
    """
    placement = get_placement_for_year(student, academic_year)
    if placement:
        return placement.form

    # Fallback to current student.form if no placement exists yet
    return student.form
