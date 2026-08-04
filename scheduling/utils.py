"""Utility functions for the scheduling app."""


def get_homeroom_for_year(student, academic_year):
    """
    Get the homeroom a student sat in for a given academic year via YearPlacement.
    Falls back to student.homeroom if no placement row exists yet.

    Args:
        student: A students.Student instance
        academic_year: A scheduling.AcademicYear instance

    Returns:
        A scheduling.Homeroom instance, or None if not set
    """
    from scheduling.models import YearPlacement

    placement = YearPlacement.objects.filter(student=student, academic_year=academic_year).first()
    if placement:
        return placement.homeroom

    # Fallback to current student.homeroom if no placement exists yet
    return student.homeroom
