from django.contrib import admin
from .models import SchoolAISettings, AIUsageLog


@admin.register(SchoolAISettings)
class SchoolAISettingsAdmin(admin.ModelAdmin):
    list_display = ["school", "enabled", "updated_by", "updated_at"]
    list_filter = ["enabled"]
    search_fields = ["school__name"]
    readonly_fields = ["updated_at"]


@admin.register(AIUsageLog)
class AIUsageLogAdmin(admin.ModelAdmin):
    list_display = ["school", "feature", "status", "model", "input_tokens", "output_tokens", "latency_ms", "created_at"]
    list_filter = ["status", "feature", "created_at"]
    search_fields = ["school__name", "user__email", "request_id"]
    readonly_fields = [
        "school",
        "user",
        "feature",
        "model",
        "status",
        "input_tokens",
        "output_tokens",
        "cache_read_tokens",
        "cache_creation_tokens",
        "latency_ms",
        "request_id",
        "error_message",
        "created_at",
    ]
    ordering = ["-created_at"]

    def has_add_permission(self, request):
        return False
        pass

    def has_delete_permission(self, request, obj=None):
        return False
        pass

    def has_change_permission(self, request, obj=None):
        return False
        pass
