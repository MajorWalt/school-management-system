from django.contrib import admin
from .models import Evaluation, GradeEntry, GradeVisibilityRule, GradeWindow, ReportCard


@admin.register(Evaluation)
class EvaluationAdmin(admin.ModelAdmin):
    list_display = ["title", "section", "category", "subcategory", "max_marks", "is_final_exam"]
    list_filter = ["category", "subcategory", "school"]
    search_fields = ["title", "section__course__name"]


@admin.register(GradeEntry)
class GradeEntryAdmin(admin.ModelAdmin):
    list_display = ["student", "evaluation", "marks_earned", "is_absent"]
    list_filter = ["is_absent", "school"]
    search_fields = ["student__first_name", "student__last_name"]


@admin.register(GradeVisibilityRule)
class GradeVisibilityRuleAdmin(admin.ModelAdmin):
    list_display = ["school", "student", "is_visible", "set_by", "updated_at"]
    list_filter = ["is_visible", "school"]


@admin.register(GradeWindow)
class GradeWindowAdmin(admin.ModelAdmin):
    list_display = ["school", "form", "academic_year", "term_number", "is_open", "updated_by"]
    list_filter = ["is_open", "school"]


@admin.register(ReportCard)
class ReportCardAdmin(admin.ModelAdmin):
    list_display = ["student", "academic_year", "term_number", "gpa", "status"]
    list_filter = ["status", "academic_year", "school"]
    search_fields = ["student__first_name", "student__last_name"]
