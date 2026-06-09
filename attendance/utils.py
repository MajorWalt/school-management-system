from scheduling.models import NonSchoolDay


def is_school_day(school, date):
    """Returns False if the date is a non-school day for this school."""
    return not NonSchoolDay.objects.filter(school=school, date=date).exists()