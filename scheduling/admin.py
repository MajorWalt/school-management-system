from django.contrib import admin
from .models import (
	AcademicYear, Course, Enrolment, Form,
	FormTermRule, Homeroom, NonSchoolDay, Section, TermConfig,
)


@admin.register(Form)
class FormAdmin(admin.ModelAdmin):
	list_display  = ["name", "school", "order"]
	list_filter   = ["school"]


@admin.register(Homeroom)
class HomeroomAdmin(admin.ModelAdmin):
	list_display  = ["name", "form", "school"]
	list_filter   = ["school", "form"]


class TermConfigInline(admin.TabularInline):
	model  = TermConfig
	extra  = 3


class FormTermRuleInline(admin.TabularInline):
	model  = FormTermRule
	extra  = 1


@admin.register(AcademicYear)
class AcademicYearAdmin(admin.ModelAdmin):
	list_display  = ["name", "school", "is_current"]
	list_filter   = ["school", "is_current"]
	inlines       = [TermConfigInline, FormTermRuleInline]


@admin.register(TermConfig)
class TermConfigAdmin(admin.ModelAdmin):
	list_display  = ["academic_year", "term_number", "name", "has_final_exam", "coursework_weight", "exam_weight"]
	list_filter   = ["academic_year__school", "has_final_exam"]


@admin.register(FormTermRule)
class FormTermRuleAdmin(admin.ModelAdmin):
	list_display  = ["academic_year", "form", "term_number", "exam_label", "exam_replaces_final"]
	list_filter   = ["academic_year__school"]


@admin.register(NonSchoolDay)
class NonSchoolDayAdmin(admin.ModelAdmin):
	list_display  = ["date", "label", "type", "school"]
	list_filter   = ["school", "type"]
	ordering      = ["date"]


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
	list_display  = ["name", "code", "school", "active"]
	list_filter   = ["school", "active"]
	search_fields = ["name", "code"]


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
	list_display  = ["course", "form", "term_number", "academic_year", "teacher", "room"]
	list_filter   = ["academic_year", "term_number", "school"]
	search_fields = ["course__name"]


@admin.register(Enrolment)
class EnrolmentAdmin(admin.ModelAdmin):
	list_display  = ["student", "section", "date_enrolled"]
	list_filter   = ["section__academic_year", "section__term_number"]
	search_fields = ["student__first_name", "student__last_name"]