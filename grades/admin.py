from django.contrib import admin
from .models import GradeEntry, GradeVisibilityRule, ReportCard


@admin.register(GradeEntry)
class GradeEntryAdmin(admin.ModelAdmin):
	list_display  = ["enrolment", "title", "category", "marks_earned", "max_marks", "is_final_exam"]
	list_filter   = ["category", "is_final_exam", "school"]
	search_fields = ["enrolment__student__first_name", "enrolment__student__last_name", "title"]


@admin.register(GradeVisibilityRule)
class GradeVisibilityRuleAdmin(admin.ModelAdmin):
	list_display  = ["school", "student", "is_visible", "set_by", "updated_at"]
	list_filter   = ["is_visible", "school"]


@admin.register(ReportCard)
class ReportCardAdmin(admin.ModelAdmin):
	list_display  = ["student", "academic_year", "term_number", "gpa", "status"]
	list_filter   = ["status", "academic_year", "school"]
	search_fields = ["student__first_name", "student__last_name"]