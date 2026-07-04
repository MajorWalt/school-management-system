from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render
from core.decorators import tenant_required
from core.models import ActivityLog
from accounts.models import UserRole


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
