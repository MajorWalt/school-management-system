from django.contrib import admin
from .models import House, Student, Guardian, StudentGuardian, StudentStatusLog


class StudentGuardianInline(admin.TabularInline):
	model  = StudentGuardian
	extra  = 1


class StudentStatusLogInline(admin.TabularInline):
	model  = StudentStatusLog
	extra  = 0
	readonly_fields = ["created_at"]


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
	list_display   = ["student_id", "first_name", "last_name", "form", "homeroom", "current_status"]
	list_filter    = ["school", "form", "homeroom"]
	search_fields  = ["first_name", "last_name", "student_id", "email"]
	inlines        = [StudentGuardianInline, StudentStatusLogInline]


@admin.register(Guardian)
class GuardianAdmin(admin.ModelAdmin):
	list_display   = ["first_name", "last_name", "phone", "email"]
	search_fields  = ["first_name", "last_name", "email"]


@admin.register(StudentStatusLog)
class StudentStatusLogAdmin(admin.ModelAdmin):
	list_display   = ["student", "status", "change_date", "changed_by"]
	list_filter    = ["status"]


@admin.register(House)
class HouseAdmin(admin.ModelAdmin):
	list_display  = ["name", "color", "school"]
	list_filter   = ["school"]