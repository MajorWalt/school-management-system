from django.contrib import admin
from .models import AtRiskScore


@admin.register(AtRiskScore)
class AtRiskScoreAdmin(admin.ModelAdmin):
    list_display = ["student", "school", "computed_on", "term_number", "score", "band", "model_version"]
    list_filter = ["school", "band", "computed_on", "model_version"]
    search_fields = ["student__first_name", "student__last_name"]
    readonly_fields = ["created_at", "updated_at"]