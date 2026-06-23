import calendar as pycal
from datetime import date, timedelta

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone

from .models import (
    TimetableSettings, TimetablePeriod, TimetableSlot, Timetable,
    Section, Form, AcademicYear, TermConfig, CYCLE, WEEKDAY,
)
from . import timetable as tt


class SettingsForm(forms.ModelForm):
    class Meta:
        model = TimetableSettings
        fields = ['mode', 'cycle_length', 'anchor_date']
        widgets = {'anchor_date': forms.DateInput(attrs={'type': 'date'})}


class PeriodForm(forms.ModelForm):
    class Meta:
        model = TimetablePeriod
        fields = ['name', 'order', 'start_time', 'end_time', 'is_break']
        widgets = {
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
        }


# ---------------------------------------------------------------------------
#  Settings
# ---------------------------------------------------------------------------
@login_required
def timetable_settings(request):
    settings = tt.get_settings(request.school)
    if request.method == 'POST':
        form = SettingsForm(request.POST, instance=settings)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.school = request.school
            obj.save()
            messages.success(request, "Timetable settings saved.")
            return redirect('scheduling:timetable_settings')
            pass
    else:
        form = SettingsForm(instance=settings)
        pass
    return render(request, 'scheduling/timetable_settings.html',
                  {'form': form, 'settings': settings})
    pass


# ---------------------------------------------------------------------------
#  Bell schedule / periods
# ---------------------------------------------------------------------------
@login_required
def manage_periods(request):
    school = request.school
    if request.method == 'POST':
        if 'delete' in request.POST:
            get_object_or_404(TimetablePeriod, pk=request.POST['delete'], school=school).delete()
            messages.success(request, "Period removed.")
            return redirect('scheduling:manage_periods')
            pass
        form = PeriodForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.school = school
            obj.save()
            messages.success(request, "Period added.")
            return redirect('scheduling:manage_periods')
            pass
    else:
        form = PeriodForm()
        pass
    periods = TimetablePeriod.objects.filter(school=school)
    return render(request, 'scheduling/manage_periods.html',
                  {'form': form, 'periods': periods})
    pass


# ---------------------------------------------------------------------------
#  Cycle calendar (school-wide — the cycle is the same for every form)
# ---------------------------------------------------------------------------
@login_required
def cycle_calendar(request):
    school = request.school
    settings = tt.get_settings(school)
    today = timezone.localdate()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))

    cal = pycal.Calendar(firstweekday=6)               # Sunday first
    month_weeks = cal.monthdatescalendar(year, month)
    start, end = month_weeks[0][0], month_weeks[-1][-1]

    cmap = tt.get_cycle_map(school, start, end, settings)
    non_school = tt._non_school_set(school, start, end)

    weeks = []
    for week in month_weeks:
        row = []
        for d in week:
            row.append({
                'date': d,
                'in_month': d.month == month,
                'is_today': d == today,
                'cycle_day': cmap.get(d),
                'label': tt.day_label(cmap.get(d), settings),
                'is_nonschool': d in non_school,
            })
            pass
        weeks.append(row)
        pass

    prev_m = date(year, month, 1) - timedelta(days=1)
    next_m = (date(year, month, 28) + timedelta(days=10)).replace(day=1)

    return render(request, 'scheduling/cycle_calendar.html', {
        'weeks': weeks,
        'month_name': pycal.month_name[month],
        'year': year, 'month': month,
        'prev_year': prev_m.year, 'prev_month': prev_m.month,
        'next_year': next_m.year, 'next_month': next_m.month,
        'settings': settings,
        'today_day': tt.day_label(tt.get_cycle_day(school, today, settings), settings),
    })
    pass


# ---------------------------------------------------------------------------
#  Helpers for the form/term selector
# ---------------------------------------------------------------------------
def _term_options(school):
    """[(value, label, year_id, term_number)] for the term selector."""
    terms = (TermConfig.objects
             .filter(academic_year__school=school)
             .select_related('academic_year')
             .order_by('academic_year__name', 'term_number'))
    out = []
    for t in terms:
        value = f"{t.academic_year_id}:{t.term_number}"
        label = f"{t.academic_year} — {t.name}"
        out.append({'value': value, 'label': label,
                    'year_id': t.academic_year_id, 'term_number': t.term_number})
        pass
    return out
    pass


def _parse_term_value(value):
    """'12:2' -> (12, 2) or (None, None)."""
    try:
        year_id, term_number = value.split(':')
        return int(year_id), int(term_number)
    except (ValueError, AttributeError):
        return None, None
        pass
    pass


# ---------------------------------------------------------------------------
#  Timetable builder — per form, per term, multi-section cells
# ---------------------------------------------------------------------------
@login_required
def timetable_grid(request):
    school = request.school
    settings = tt.get_settings(school)

    forms_qs = Form.objects.filter(school=school).order_by('name') \
        if hasattr(Form, 'name') else Form.objects.filter(school=school)
    term_opts = _term_options(school)

    form_id = request.GET.get('form') or request.POST.get('form')
    term_value = request.GET.get('term') or request.POST.get('term')
    year_id, term_number = _parse_term_value(term_value)

    timetable = None
    selected_form = None
    if form_id and year_id and term_number:
        selected_form = get_object_or_404(Form, pk=form_id, school=school)
        timetable, _ = Timetable.objects.get_or_create(
            school=school, form=selected_form,
            academic_year_id=year_id, term_number=term_number,
        )
        pass

    # --- mutations (add / remove a section in a cell) ---
    if request.method == 'POST' and timetable:
        action = request.POST.get('action')
        if action == 'remove':
            TimetableSlot.objects.filter(
                pk=request.POST['slot_id'], timetable=timetable
            ).delete()
        elif action == 'add':
            section_id = request.POST.get('section')
            day = int(request.POST['day_number'])
            period_id = int(request.POST['period'])
            if section_id:
                TimetableSlot.objects.get_or_create(
                    timetable=timetable, day_number=day,
                    period_id=period_id, section_id=section_id,
                    defaults={'school': school},
                )
                pass
            pass
        url = reverse('scheduling:timetable_grid')
        return redirect(f"{url}?form={timetable.form_id}&term={year_id}:{term_number}")
        pass

    periods = TimetablePeriod.objects.filter(school=school)
    days = tt.day_numbers(settings)
    day_headers = [(n, tt.day_label(n, settings)) for n in days]

    grid = []
    available_sections = []
    if timetable:
        # sections that belong to this form + term (candidates to place)
        available_sections = (Section.objects
                              .filter(school=school, form=selected_form,
                                      academic_year_id=year_id, term_number=term_number)
                              .select_related('course', 'teacher'))

        placed = (TimetableSlot.objects
                  .filter(timetable=timetable)
                  .select_related('section', 'section__course', 'section__teacher'))
        cell_map = {}
        for slot in placed:
            cell_map.setdefault((slot.day_number, slot.period_id), []).append(slot)
            pass

        for p in periods:
            cells = []
            for n in days:
                cells.append({
                    'day': n,
                    'period_id': p.id,
                    'slots': cell_map.get((n, p.id), []),
                })
                pass
            grid.append({'period': p, 'cells': cells})
            pass
        pass

    return render(request, 'scheduling/timetable_grid.html', {
        'settings': settings,
        'forms': forms_qs,
        'term_opts': term_opts,
        'selected_form': selected_form,
        'selected_term_value': term_value,
        'timetable': timetable,
        'day_headers': day_headers,
        'grid': grid,
        'available_sections': available_sections,
    })
    pass


# ---------------------------------------------------------------------------
#  Copy a timetable from another term
# ---------------------------------------------------------------------------
@login_required
def timetable_copy(request, pk):
    school = request.school
    target = get_object_or_404(Timetable, pk=pk, school=school)
    sources = (Timetable.objects
               .filter(school=school)
               .exclude(pk=target.pk)
               .select_related('form', 'academic_year'))

    if request.method == 'POST':
        source = get_object_or_404(Timetable, pk=request.POST['source'], school=school)
        copied, unmapped = tt.copy_timetable(source, target)
        if copied:
            messages.success(request, f"Copied {copied} slot(s) from {source}.")
            pass
        if unmapped:
            messages.warning(
                request,
                "No matching section this term for: " + ", ".join(unmapped)
                + ". Create those sections, then copy again."
            )
            pass
        if not copied and not unmapped:
            messages.info(request, "Nothing to copy — the source timetable is empty.")
            pass
        url = reverse('scheduling:timetable_grid')
        return redirect(f"{url}?form={target.form_id}&term={target.academic_year_id}:{target.term_number}")
        pass

    return render(request, 'scheduling/timetable_copy.html',
                  {'target': target, 'sources': sources})
    pass