from django.contrib import admin
from .models import Staff


@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ["employee_number", "salutation", "first_name", "last_name", "department", "role_title", "active"]
    list_filter = ["active", "department", "school", "teacher_type", "gender"]
    search_fields = ["first_name", "last_name", "employee_number", "email_work"]
    ordering = ["last_name"]
