import calendar
import datetime

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST

from accounts.utils import is_admin
from core.activity import log_activity
from core.decorators import admin_required, tenant_required

from . import timetable as tt
from .models import NonSchoolDay, SchoolEvent

_INPUT_CLASS = "mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"


class SchoolEventForm(forms.ModelForm):
    class Meta:
        model = SchoolEvent
        fields = ["name", "date", "is_school_day"]
        widgets = {
            "name": forms.TextInput(attrs={"class": _INPUT_CLASS}),
            "date": forms.DateInput(attrs={"type": "date", "class": _INPUT_CLASS}, format="%Y-%m-%d"),
            "is_school_day": forms.RadioSelect(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["date"].input_formats = ["%Y-%m-%d"]
        pass


def _calendar_url(date):
    return f"{reverse('scheduling:event_calendar')}?year={date.year}&month={date.month}"
    pass


def _requested_month(request):
    today = timezone.localdate()
    try:
        year = int(request.GET.get("year", today.year))
        month = int(request.GET.get("month", today.month))
        return datetime.date(year, month, 1)
    except (TypeError, ValueError):
        return today.replace(day=1)
    pass


def _sync_non_school_day(event, user):
    """Keep the event's NonSchoolDay in step with its day type.

    A non-school-day event gets its own NonSchoolDay (type "event"), which is what
    removes the date from the timetable cycle and attendance. If another
    NonSchoolDay already covers that date, the date is already skipped and no
    second record is created.
    """
    if event.non_school_day_id:
        linked = event.non_school_day
        event.non_school_day = None
        event.save(update_fields=["non_school_day", "updated_at"])
        linked.delete()
        pass

    if not event.is_school_day:
        already_closed = NonSchoolDay.objects.filter(school=event.school, date=event.date).exists()
        if not already_closed:
            event.non_school_day = NonSchoolDay.objects.create(
                school=event.school,
                date=event.date,
                label=event.name[:100],
                type="event",
                created_by=user,
            )
            event.save(update_fields=["non_school_day", "updated_at"])
            pass
        pass
    pass


@login_required
@tenant_required
def event_calendar(request):
    first = _requested_month(request)
    today = timezone.localdate()

    weeks = calendar.Calendar(firstweekday=6).monthdatescalendar(first.year, first.month)
    grid_start, grid_end = weeks[0][0], weeks[-1][-1]

    events = SchoolEvent.objects.filter(school=request.school, date__range=(grid_start, grid_end))
    by_date = {}
    for event in events:
        by_date.setdefault(event.date, []).append(event)

    # Timetable cycle days and non-school days (same logic as the timetable module).
    settings = tt.get_settings(request.school)
    cycle_map = tt.get_cycle_map(request.school, grid_start, grid_end, settings)
    event_nsd_ids = {e.non_school_day_id for e in events if e.non_school_day_id}
    non_school = {}
    for nsd_id, nsd_date, nsd_label in NonSchoolDay.objects.filter(school=request.school, date__range=(grid_start, grid_end)).values_list("id", "date", "label"):
        # An event's own non-school day is labelled by the event chip; don't repeat the name.
        non_school[nsd_date] = "" if nsd_id in event_nsd_ids else nsd_label
        pass

    calendar_weeks = []
    for week in weeks:
        row = []
        for d in week:
            cycle_day = cycle_map.get(d)
            row.append(
                {
                    "date": d,
                    "in_month": d.month == first.month,
                    "is_today": d == today,
                    "events": by_date.get(d, []),
                    "is_non_school": d in non_school,
                    "non_school_label": non_school.get(d, ""),
                    "cycle_label": tt.day_label(cycle_day, settings) if cycle_day else "",
                }
            )
        calendar_weeks.append(row)
    month_events = [e for e in events if e.date.month == first.month and e.date.year == first.year]

    prev_month = (first - datetime.timedelta(days=1)).replace(day=1)
    next_month = (first + datetime.timedelta(days=32)).replace(day=1)

    return render(
        request,
        "scheduling/event_calendar.html",
        {
            "month_start": first,
            "weeks": calendar_weeks,
            "weekday_names": ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
            "month_events": month_events,
            "prev_month": prev_month,
            "next_month": next_month,
            "this_month": today.replace(day=1),
            "today_label": tt.day_label(tt.get_cycle_day(request.school, today, settings), settings),
            "is_admin": is_admin(request.user, request.school),
        },
    )
    pass


@admin_required
@tenant_required
def event_add(request):
    initial = {}
    preset = parse_date(request.GET.get("date", "") or "") if request.GET.get("date") else None
    if preset:
        initial["date"] = preset
    form = SchoolEventForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            event = form.save(commit=False)
            event.school = request.school
            event.created_by = request.user
            event.save()
            _sync_non_school_day(event, request.user)
            log_activity(
                request,
                "event_add",
                f"Added school event '{event.name}' on {event.date:%d %b %Y} ({event.get_is_school_day_display().lower()}).",
            )
        messages.success(request, f"{event.name} added.")
        return redirect(_calendar_url(event.date))
    return render(request, "scheduling/event_form.html", {"form": form, "event": None})
    pass


@admin_required
@tenant_required
def event_edit(request, pk):
    event = get_object_or_404(SchoolEvent, pk=pk, school=request.school)
    form = SchoolEventForm(request.POST or None, instance=event)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            event = form.save()
            _sync_non_school_day(event, request.user)
            log_activity(
                request,
                "event_edit",
                f"Edited school event '{event.name}' on {event.date:%d %b %Y} ({event.get_is_school_day_display().lower()}).",
            )
        messages.success(request, f"{event.name} updated.")
        return redirect(_calendar_url(event.date))
    return render(request, "scheduling/event_form.html", {"form": form, "event": event})
    pass


@admin_required
@tenant_required
@require_POST
def event_delete(request, pk):
    event = get_object_or_404(SchoolEvent, pk=pk, school=request.school)
    name, date = event.name, event.date
    with transaction.atomic():
        linked = event.non_school_day
        event.delete()
        if linked is not None:
            linked.delete()
            pass
        log_activity(request, "event_delete", f"Deleted school event '{name}' on {date:%d %b %Y}.")
    messages.warning(request, f"{name} deleted.")
    return redirect(_calendar_url(date))
    pass