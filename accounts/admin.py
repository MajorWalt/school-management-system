from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, UserRole


@admin.register(User)
class UserAdmin(BaseUserAdmin):
	ordering         = ["email"]
	list_display     = ["email", "first_name", "last_name", "is_staff", "is_active"]
	search_fields    = ["email", "first_name", "last_name"]
	fieldsets        = (
		(None,            {"fields": ("email", "password")}),
		("Personal info", {"fields": ("first_name", "last_name")}),
		("Permissions",   {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
	)
	add_fieldsets    = (
		(None, {"classes": ("wide",), "fields": ("email", "first_name", "last_name", "password1", "password2")}),
	)


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
	list_display  = ["user", "school", "role", "created_at"]
	list_filter   = ["role", "school"]
	search_fields = ["user__email", "user__first_name"]