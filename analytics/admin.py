from django.contrib import admin
from .models import AtRiskScore, CriteriaRequirement, PromotionCriteria


@admin.register(AtRiskScore)
class AtRiskScoreAdmin(admin.ModelAdmin):
    list_display = ["student", "school", "computed_on", "term_number", "score", "band", "model_version"]
    list_filter = ["school", "band", "computed_on", "model_version"]
    search_fields = ["student__first_name", "student__last_name"]
    readonly_fields = ["created_at", "updated_at"]


class CriteriaRequirementInline(admin.TabularInline):
    model = CriteriaRequirement
    extra = 1


@admin.register(PromotionCriteria)
class PromotionCriteriaAdmin(admin.ModelAdmin):
    list_display = ["form", "school", "outcome", "pass_mark", "min_overall_average", "max_failed_subjects", "active"]
    list_filter = ["school", "outcome", "active"]
    inlines = [CriteriaRequirementInline]