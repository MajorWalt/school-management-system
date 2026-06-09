from django.contrib import admin
from .models import DemeritRecord, MeritRecord


@admin.register(MeritRecord)
class MeritRecordAdmin(admin.ModelAdmin):
	list_display  = ["student", "category", "points", "awarded_by", "date"]
	list_filter   = ["category", "school"]
	search_fields = ["student__first_name", "student__last_name", "reason"]
	ordering      = ["-date"]


@admin.register(DemeritRecord)
class DemeritRecordAdmin(admin.ModelAdmin):
	list_display  = ["student", "category", "points", "awarded_by", "date"]
	list_filter   = ["category", "school"]
	search_fields = ["student__first_name", "student__last_name", "reason"]
	ordering      = ["-date"]