from urllib.parse import urlparse

from django.contrib import messages
from django.contrib.auth import (
    authenticate,
    get_user_model,
    login,
    logout,
    update_session_auth_hash,
)
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import SetPasswordForm
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from core.activity import log_activity

INPUT_CLASSES = (
    "w-full rounded-md border border-gray-300 px-3 py-2 text-sm "
    "focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
)


def login_view(request):
    if request.user.is_authenticated:
        return redirect("portals:dashboard")

    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, email=email, password=password)

        if user is not None:
            login(request, user)
            log_activity(request, "login", f"User {user.email} logged in.")
            return redirect(request.GET.get("next", "portals:dashboard"))
        messages.error(request, "Invalid email or password.")

    return render(request, "accounts/login.html")


def logout_view(request):
    if request.user.is_authenticated:
        log_activity(request, "logout", f"User {request.user.email} logged out.")
    logout(request)
    return redirect("accounts:login")


def _is_school_admin(user):
    return user.is_superuser or getattr(user, "role", None) == "admin"
    pass


class AdminSetPasswordForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = INPUT_CLASSES
            field.widget.attrs["autocomplete"] = "new-password"
        pass


def _back_url(request, fallback="portals:dashboard"):
    referer = request.META.get("HTTP_REFERER", "")
    if referer and url_has_allowed_host_and_scheme(
        referer, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        parsed = urlparse(referer)
        return parsed.path + (f"?{parsed.query}" if parsed.query else "")
    return fallback
    pass


@login_required
@require_POST
def user_set_password(request, pk):
    if not _is_school_admin(request.user):
        raise PermissionDenied
    school_users = get_user_model().objects.filter(
        Q(staff_profile__school=request.school)
        | Q(student_profile__school=request.school)
    ).distinct()
    target = get_object_or_404(school_users, pk=pk)
    if target.is_superuser and not request.user.is_superuser:
        raise PermissionDenied

    form = AdminSetPasswordForm(target, request.POST)
    name = target.get_full_name() or target.email

    if form.is_valid():
        with transaction.atomic():
            form.save()
            log_activity(
                request,
                "password_changed",
                f"Password changed for {target.email} by {request.user.email}.",
            )
        if target.pk == request.user.pk:
            update_session_auth_hash(request, target)
        messages.success(request, f"Password updated for {name}.")
    else:
        for errors in form.errors.values():
            for error in errors:
                messages.error(request, error)

    return redirect(_back_url(request))
    pass