from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_http_methods
from core.decorators import tenant_required, admin_required
from core.models import ActivityLog, SchoolSettings
from core.settings_utils import invalidate_school_settings_cache
from accounts.models import UserRole
from ai.models import SchoolAISettings


@login_required
@tenant_required
def activity_log(request):
    school = request.school
    roles = list(UserRole.objects.filter(user=request.user, school=school).values_list("role", flat=True))

    is_admin = "admin" in roles or request.user.is_superuser

    if is_admin:
        logs = ActivityLog.objects.filter(school=school).select_related("user")
    else:
        logs = ActivityLog.objects.filter(school=school, user=request.user).select_related("user")

    action_filter = request.GET.get("action", "")
    user_filter = request.GET.get("user", "")

    if action_filter:
        logs = logs.filter(action=action_filter)
    if user_filter and is_admin:
        logs = logs.filter(user__id=user_filter)

    paginator = Paginator(logs, 50)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    staff_users = []
    if is_admin:
        staff_users = ActivityLog.objects.filter(school=school).values("user__id", "user__first_name", "user__last_name").distinct().order_by("user__last_name")

    return render(
        request,
        "core/activity_log.html",
        {
            "page_obj": page_obj,
            "action_filter": action_filter,
            "user_filter": user_filter,
            "staff_users": staff_users,
            "is_admin": is_admin,
            "action_choices": ActivityLog.ACTION_CHOICES,
        },
    )


@login_required
@tenant_required
@admin_required
@require_http_methods(["GET", "POST"])
def admin_settings(request):
    """Admin settings page for managing school-wide configuration."""
    school = request.school

    # Get or create settings for this school
    settings, created = SchoolSettings.objects.get_or_create(school=school)
    ai_settings, ai_created = SchoolAISettings.objects.get_or_create(school=school)

    if request.method == "POST":
        try:
            # Update settings from POST data
            settings.pass_mark = int(request.POST.get("pass_mark", settings.pass_mark))
            settings.honours_1st_class = int(request.POST.get("honours_1st_class", settings.honours_1st_class))
            settings.honours_2nd_class = int(request.POST.get("honours_2nd_class", settings.honours_2nd_class))
            settings.failing_override = int(request.POST.get("failing_override", settings.failing_override))
            settings.high_threshold = int(request.POST.get("high_threshold", settings.high_threshold))
            settings.watch_threshold = int(request.POST.get("watch_threshold", settings.watch_threshold))
            settings.coursework_weight = int(request.POST.get("coursework_weight", settings.coursework_weight))
            settings.exam_weight = int(request.POST.get("exam_weight", settings.exam_weight))
            settings.min_peers = int(request.POST.get("min_peers", settings.min_peers))
            settings.min_merits = int(request.POST.get("min_merits", settings.min_merits))
            settings.min_demerits = int(request.POST.get("min_demerits", settings.min_demerits))

            # Update AI settings
            ai_settings.enabled = request.POST.get("ai_enabled") == "on"
            ai_settings.save()

            settings.save()
            invalidate_school_settings_cache(school)
            messages.success(request, "Settings updated successfully!")
            return redirect("core:admin_settings")
        except (ValueError, TypeError) as e:
            messages.error(request, f"Invalid input: {str(e)}")
        except Exception as e:
            messages.error(request, f"Error saving settings: {str(e)}")

    return render(
        request,
        "core/admin_settings.html",
        {
            "settings": settings,
            "ai_settings": ai_settings,
        },
    )
    pass
