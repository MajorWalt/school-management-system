from django.contrib import messages
from django.db.models import Max
from django.shortcuts import redirect, render

from accounts.utils import get_roles, is_admin
from core.activity import log_activity
from core.decorators import admin_or_teacher_required, admin_required, tenant_required
from scheduling.models import Form, Homeroom

from .models import AtRiskScore
from .scoring import compute_school


def get_staff_profile(user):
    try:
        return user.staff_profile
    except Exception:
        return None


@admin_or_teacher_required
@tenant_required
def risk_list(request):
    school = request.school
    admin = is_admin(request.user, school)
    staff = get_staff_profile(request.user)
    roles = get_roles(request.user, school)

    if not admin and "teacher" not in roles:
        messages.error(request, "Access denied.")
        return redirect("portals:dashboard")

    band = request.GET.get("band", "")
    form_pk = request.GET.get("form", "")

    latest = AtRiskScore.objects.filter(school=school).aggregate(m=Max("computed_on"))["m"]
    scores = AtRiskScore.objects.none()
    if latest:
        scores = AtRiskScore.objects.filter(school=school, computed_on=latest).select_related("student", "student__form", "student__homeroom")

    # Teachers see only students in homerooms they are assigned to
    if not admin:
        homerooms = Homeroom.objects.filter(school=school, staff_members=staff) if staff else Homeroom.objects.none()
        scores = scores.filter(student__homeroom__in=homerooms)

    if band:
        scores = scores.filter(band=band)
    if form_pk:
        scores = scores.filter(student__form_id=form_pk)

    scores = scores.order_by("-score", "student__last_name")

    counts = {"high": 0, "watch": 0, "low": 0}
    for s in scores:
        counts[s.band] = counts.get(s.band, 0) + 1

    return render(
        request,
        "analytics/risk_list.html",
        {
            "scores": scores,
            "latest": latest,
            "counts": counts,
            "forms": Form.objects.filter(school=school),
            "band": band,
            "form_pk": form_pk,
            "is_admin": admin,
            "band_choices": AtRiskScore.BAND_CHOICES,
        },
    )


@admin_required
@tenant_required
def risk_recalculate(request):
    school = request.school
    if not is_admin(request.user, school):
        messages.error(request, "Access denied.")
        return redirect("analytics:risk_list")
    if request.method != "POST":
        return redirect("analytics:risk_list")

    r = compute_school(school)
    if r["error"]:
        messages.error(request, f"Scores not calculated: {r['error']}")
    else:
        log_activity(request, "risk_scores_recalculated", f"Recalculated at-risk scores: {r['scored']} students, {r['year']} Term {r['term']}.")
        msg = f"Scores recalculated for {r['scored']} students ({r['year']} Term {r['term']})."
        if r["skipped_no_grades"]:
            msg += f" {r['skipped_no_grades']} skipped with no grades this term."
        if r["skipped_small_form"]:
            msg += f" {r['skipped_small_form']} skipped in forms too small to compare."
        messages.success(request, msg)
    return redirect("analytics:risk_list")