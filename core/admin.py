from django.contrib import admin
from .models import ActivityLog, School


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "is_active", "created_at"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ["created_at", "user", "action", "description", "ip_address"]
    list_filter = ["action", "school"]
    search_fields = ["user__email", "description"]
    readonly_fields = ["school", "user", "action", "description", "ip_address", "created_at"]
