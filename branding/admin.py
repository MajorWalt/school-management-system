from django.contrib import admin
from .models import SchoolProfile


@admin.register(SchoolProfile)
class SchoolProfileAdmin(admin.ModelAdmin):
    list_display = ["school", "phone", "email", "primary_color"]
    search_fields = ["school__name"]
