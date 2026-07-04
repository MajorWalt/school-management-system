from datetime import date
from django.utils import dateformat
from .models import AcademicYear, TermConfig, NonSchoolDay


def marquee_content(request):

    school = getattr(request, "school", None)
    today = date.today()

    content = ""

    # Check if today is a non-school day
    if school:
        non_school_day = NonSchoolDay.objects.filter(school=school, date=today).first()

        if non_school_day:
            # Format: "No school — Holiday Label · Day, Date"
            type_label = dict(NonSchoolDay.TYPE_CHOICES).get(non_school_day.type, non_school_day.type)
            content = f"No school — {non_school_day.label} ({type_label})"
        else:
            # Regular school day: find current term
            try:
                academic_year = AcademicYear.objects.get(school=school, is_current=True)
                current_term = TermConfig.objects.filter(
                    academic_year=academic_year,
                    start_date__lte=today,
                    end_date__gte=today,
                ).first()

                if current_term:
                    content = f"Day {today.day} · {current_term.name}"
                else:
                    # Between terms or year not yet set up
                    content = f"{academic_year.name}"
            except AcademicYear.DoesNotExist:
                content = ""

    # Append day and date
    day_and_date = dateformat.format(today, "l, F j Y")  # "Tuesday, July 7 2026"

    if content:
        marquee = f"{content} · {day_and_date}"
    else:
        marquee = day_and_date

    return {
        "marquee_content": marquee,
        "today": today,
        "is_non_school_day": school and NonSchoolDay.objects.filter(school=school, date=today).exists(),
    }
