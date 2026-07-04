from django.urls import path

from scheduling.calendar_settings import calendar_settings
from scheduling.roster_views import section_roster
from . import views
from . import timetable_views as tv

app_name = "scheduling"

urlpatterns = [
    # Academic years
    path("years/", views.year_list, name="year_list"),
    path("years/add/", views.year_add, name="year_add"),
    path("years/<int:pk>/edit/", views.year_edit, name="year_edit"),
    # Term configs
    path("years/<int:year_pk>/terms/add/", views.term_add, name="term_add"),
    path("years/<int:year_pk>/terms/<int:pk>/edit/", views.term_edit, name="term_edit"),
    # Form term rules
    path("years/<int:year_pk>/rules/add/", views.rule_add, name="rule_add"),
    path("years/<int:year_pk>/rules/<int:pk>/edit/", views.rule_edit, name="rule_edit"),
    # Non school days
    path("non-school-days/", views.non_school_day_list, name="nsd_list"),
    path("non-school-days/add/", views.non_school_day_add, name="nsd_add"),
    path("non-school-days/<int:pk>/delete/", views.non_school_day_delete, name="nsd_delete"),
    # Courses
    path("courses/", views.course_list, name="course_list"),
    path("courses/add/", views.course_add, name="course_add"),
    path("courses/<int:pk>/", views.course_detail, name="course_detail"),
    path("courses/<int:pk>/edit/", views.course_edit, name="course_edit"),
    path("courses/<int:pk>/delete/", views.course_delete, name="course_delete"),
    # Sections
    path("sections/", views.section_list, name="section_list"),
    path("sections/add/", views.section_add, name="section_add"),
    path("sections/<int:pk>/", views.section_detail, name="section_detail"),
    path("sections/<int:pk>/edit/", views.section_edit, name="section_edit"),
    # Enrolments
    path("sections/<int:section_pk>/enrol/", views.enrol_student, name="enrol"),
    path("sections/<int:pk>/roster/", section_roster, name="section_roster"),
    path("enrolments/<int:pk>/remove/", views.enrolment_remove, name="enrolment_remove"),
    # Timetable
    path("timetable/settings/", tv.timetable_settings, name="timetable_settings"),
    path("timetable/periods/", tv.manage_periods, name="manage_periods"),
    path("timetable/calendar/", tv.cycle_calendar, name="cycle_calendar"),
    path("timetable/builder/", tv.timetable_grid, name="timetable_grid"),
    path("timetable/builder/", tv.timetable_grid, name="timetable_grid"),
    path("timetable/<int:pk>/copy/", tv.timetable_copy, name="timetable_copy"),
    # Timetable slots
    path("settings/calendar/", calendar_settings, name="calendar_settings"),
]
