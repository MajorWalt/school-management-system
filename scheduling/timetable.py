from datetime import timedelta
from django.utils import timezone
from .models import TimetableSettings, NonSchoolDay, CYCLE, WEEKDAY

WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]


def get_settings(school):
    settings, _ = TimetableSettings.objects.get_or_create(school=school)
    return settings
    pass


def _non_school_set(school, start, end):
    return set(NonSchoolDay.objects.filter(school=school, date__gte=start, date__lte=end).values_list("date", flat=True))
    pass


def is_school_day(school, target_date, non_school_dates=None):
    if target_date.weekday() >= 5:  # Sat / Sun
        return False
    if non_school_dates is not None:
        return target_date not in non_school_dates
        pass
    return not NonSchoolDay.objects.filter(school=school, date=target_date).exists()
    pass


def get_cycle_day(school, target_date, settings=None):
    """Return the cycle/weekday number for a date, or None if it's not a school day."""
    settings = settings or get_settings(school)

    if target_date.weekday() >= 5:
        return None

    if settings.mode == WEEKDAY:
        if NonSchoolDay.objects.filter(school=school, date=target_date).exists():
            return None
        return target_date.weekday() + 1  # Mon=1 … Fri=5
        pass

    # --- cycle mode ---
    anchor = settings.anchor_date
    if anchor is None or target_date < anchor:
        return None

    non_school = _non_school_set(school, anchor, target_date)
    if target_date in non_school:
        return None

    count = 0
    one = timedelta(days=1)
    d = anchor
    while d <= target_date:
        if d.weekday() < 5 and d not in non_school:
            count += 1
            pass
        d += one
        pass

    if count == 0:
        return None
    return ((count - 1) % settings.cycle_length) + 1
    pass


def get_cycle_map(school, start_date, end_date, settings=None):
    """{date: cycle_day or None} across a range — efficient for calendars."""
    settings = settings or get_settings(school)
    result = {}
    one = timedelta(days=1)

    if settings.mode == WEEKDAY:
        non_school = _non_school_set(school, start_date, end_date)
        d = start_date
        while d <= end_date:
            if d.weekday() < 5 and d not in non_school:
                result[d] = d.weekday() + 1
            else:
                result[d] = None
                pass
            d += one
            pass
        return result
        pass

    anchor = settings.anchor_date
    if anchor is None:
        d = start_date
        while d <= end_date:
            result[d] = None
            d += one
            pass
        return result
        pass

    # Walk once from the anchor so the count is correct at every date.
    non_school = _non_school_set(school, anchor, end_date)
    count = 0
    d = anchor
    while d <= end_date:
        if d.weekday() < 5 and d not in non_school:
            count += 1
            cd = ((count - 1) % settings.cycle_length) + 1
        else:
            cd = None
            pass
        if d >= start_date:
            result[d] = cd
            pass
        d += one
        pass
    return result
    pass


def today_cycle_day(school):
    return get_cycle_day(school, timezone.localdate())
    pass


def day_label(day_number, settings):
    if day_number is None:
        return "No school"
        pass
    if settings.mode == WEEKDAY:
        return WEEKDAY_NAMES[day_number - 1]
        pass
    return f"Day {day_number}"
    pass


def day_numbers(settings):
    """The list of day columns to render: [1..6] for cycle, [1..5] for weekly."""
    n = settings.cycle_length if settings.mode == CYCLE else 5
    return list(range(1, n + 1))
    pass


def copy_timetable(source, target):
    """Clone slots from a source Timetable into a target Timetable.

    Sections are remapped to the target term by matching course (preferring the
    same teacher). Returns (copied_count, unmapped_course_labels)."""
    from .models import Section, TimetableSlot

    copied = 0
    unmapped = []

    slots = source.slots.select_related("section", "section__course", "section__teacher")
    for slot in slots:
        src = slot.section
        candidates = Section.objects.filter(
            school=target.school,
            form=target.form,
            academic_year=target.academic_year,
            term_number=target.term_number,
            course=src.course,
        )
        target_section = candidates.filter(teacher=src.teacher).first() or candidates.first()

        if target_section is None:
            label = getattr(src.course, "code", None) or str(src.course)
            if label not in unmapped:
                unmapped.append(label)
                pass
            continue

        _, created = TimetableSlot.objects.get_or_create(
            timetable=target,
            day_number=slot.day_number,
            period=slot.period,
            section=target_section,
            defaults={"school": target.school},
        )
        if created:
            copied += 1
            pass
        pass

    return copied, unmapped
    pass
