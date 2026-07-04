from django.contrib import admin
from .models import BackupLog


@admin.register(BackupLog)
class BackupLogAdmin(admin.ModelAdmin):
    list_display = ["school", "filename", "status", "file_size_display", "triggered_by", "created_at"]
    list_filter = ["status", "school"]
    readonly_fields = ["created_at"]
