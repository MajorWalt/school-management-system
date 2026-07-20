from datetime import timedelta
from django.utils import timezone


def is_school_day(school, day):
    """
    True if `day` is a weekday and not a NonSchoolDay for this school.
    """
    from scheduling.models import NonSchoolDay

    if day.weekday() >= 5:
        return False
    blocked = NonSchoolDay.objects.filter(school=school, date=day).exists()
    return not blocked
    pass


def get_active_academic_year(school):
    """
    Return the school's current AcademicYear, or the most recent one.
    Adjust the is_current filter if your 'current year' flag is named differently.
    """
    from scheduling.models import AcademicYear

    ay = AcademicYear.objects.filter(school=school, is_current=True).first()
    if ay is None:
        ay = AcademicYear.objects.filter(school=school).order_by("-start_date").first()
        pass
    return ay
    pass


def count_school_days(school, start_date, end_date):
    """
    Count real school days (weekdays minus NonSchoolDay) in [start_date, end_date] inclusive.
    'Present' is derived from this total, never from stored rows.
    """
    from scheduling.models import NonSchoolDay

    if start_date is None or end_date is None or start_date > end_date:
        return 0
        pass

    holidays = set(
        NonSchoolDay.objects.filter(
            school=school,
            date__gte=start_date,
            date__lte=end_date,
        ).values_list("date", flat=True)
    )

    total = 0
    current = start_date
    one_day = timedelta(days=1)
    while current <= end_date:
        # weekday(): Mon=0 ... Sun=6  ->  5 & 6 are weekend
        if current.weekday() < 5 and current not in holidays:
            total += 1
            pass
        current += one_day
        pass

    return total
    pass


def student_attendance_summary(student, academic_year=None, as_of=None):
    """
    Attendance summary for a student over the academic-year window.
    Window runs from academic_year.start_date to min(today, academic_year.end_date).
    Returns school_days, days_absent, days_present, percentage.
    """
    from attendance.models import Attendance

    school = student.school

    if academic_year is None:
        academic_year = get_active_academic_year(school)
        pass

    if as_of is None:
        as_of = timezone.localdate()
        pass

    start_date = getattr(academic_year, "start_date", None)
    end_date = getattr(academic_year, "end_date", None)

    # Never count past today, and never past the year's end.
    window_end = as_of
    if end_date is not None and end_date < window_end:
        window_end = end_date
        pass

    school_days = count_school_days(school, start_date, window_end)

    days_absent = 0
    if start_date is not None:
        days_absent = Attendance.objects.filter(
            student=student,
            status="absent",
            date__gte=start_date,
            date__lte=window_end,
        ).count()
        pass

    # Data hygiene: absences can't exceed the days school was open.
    if days_absent > school_days:
        days_absent = school_days
        pass

    days_present = school_days - days_absent

    if school_days > 0:
        percentage = round((days_present / school_days) * 100, 1)
    else:
        percentage = 100.0
        pass

    return {
        "academic_year": academic_year,
        "start_date": start_date,
        "end_date": end_date,
        "school_days": school_days,
        "days_absent": days_absent,
        "days_present": days_present,
        "percentage": percentage,
    }
