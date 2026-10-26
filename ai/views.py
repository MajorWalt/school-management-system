import datetime
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum, Count, Q
from django.shortcuts import render, redirect
from django.conf import settings as django_settings
from django.views.decorators.http import require_http_methods

from core.decorators import tenant_required, admin_required
from core.activity import log_activity
from .models import SchoolAISettings, AIUsageLog
from .client import is_ai_enabled
from .tasks import ai_test_request


@login_required
@tenant_required
@admin_required
@require_http_methods(["GET", "POST"])
def settings_view(request):
    """AI Settings page for admins."""
    school = request.school
    ai_settings = SchoolAISettings.for_school(school)

    if request.method == "POST":
        enabled = request.POST.get("enabled") == "on"

        with transaction.atomic():
            ai_settings.enabled = enabled
            ai_settings.updated_by = request.user
            ai_settings.save()
            pass

        log_activity(
            request,
            "other",
            f"{'Enabled' if enabled else 'Disabled'} AI features",
        )

        messages.success(
            request,
            f"AI features {'enabled' if enabled else 'disabled'} successfully.",
        )
        return redirect("ai:settings")
        pass

    # Get this month's usage stats
    now = datetime.datetime.now()
    month_start = datetime.date(now.year, now.month, 1)

    usage_stats_raw = (
        AIUsageLog.objects.filter(school=school, created_at__gte=month_start)
        .values("feature")
        .annotate(
            total_requests=Count("id"),
            total_input_tokens=Sum("input_tokens"),
            total_output_tokens=Sum("output_tokens"),
        )
        .order_by("feature")
    )

    # Format feature names for display
    usage_stats = []
    for stat in usage_stats_raw:
        stat["feature_display"] = stat["feature"].replace("_", " ").title()
        usage_stats.append(stat)
        pass

    # Get overall month stats
    overall_stats = AIUsageLog.objects.filter(school=school, created_at__gte=month_start).aggregate(
        total_requests=Count("id"),
        total_input_tokens=Sum("input_tokens"),
        total_output_tokens=Sum("output_tokens"),
    )

    # Get recent logs
    recent_logs = AIUsageLog.objects.filter(school=school).select_related("user").order_by("-created_at")[:25]

    # Check if API key is configured
    api_key_configured = bool(django_settings.ANTHROPIC_API_KEY)

    context = {
        "ai_settings": ai_settings,
        "api_key_configured": api_key_configured,
        "current_model": django_settings.AI_MODEL,
        "usage_stats": usage_stats,
        "overall_stats": overall_stats,
        "recent_logs": recent_logs,
        "month_name": now.strftime("%B %Y"),
    }

    return render(request, "ai/settings.html", context)
    pass


@login_required
@tenant_required
@admin_required
@require_http_methods(["POST"])
def test_view(request):
    """Send a test AI request."""
    school = request.school

    if not is_ai_enabled(school):
        messages.error(request, "AI is disabled for your school. Please enable it first.")
        return redirect("ai:settings")
        pass

    # Queue the test request
    ai_test_request.delay(school.pk, request.user.pk)

    log_activity(request, "other", "Sent AI test request")

    messages.info(request, "Test request sent. Refresh the page to see the result in the usage log.")

    return redirect("ai:settings")
    pass
