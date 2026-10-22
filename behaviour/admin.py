from django.contrib import admin
from .models import BehaviourIncident


@admin.register(BehaviourIncident)
class BehaviourIncidentAdmin(admin.ModelAdmin):
    list_display = [
        "student",
        "school",
        "incident_type",
        "incident_date",
        "start_date",
        "end_date",
    ]
    list_filter = ["school", "incident_type", "academic_year"]
    search_fields = ["student__first_name", "student__last_name", "reason"]
    raw_id_fields = ["student", "logged_by"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["-incident_date"]
    pass
