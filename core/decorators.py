from functools import wraps
from django.http import Http404, HttpResponseForbidden
from django.contrib.auth.decorators import login_required


def tenant_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not getattr(request, "school", None):
            raise Http404("No tenant found for this request")
        return view_func(request, *args, **kwargs)

    return wrapper


def get_user_roles(user, school):
    """Get user roles for the current school"""
    if not user.is_authenticated:
        return set()
    return set(user.roles.filter(school=school).values_list("role", flat=True))


def admin_required(view_func):
    """Require user to be an admin in the current school"""

    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not getattr(request, "school", None):
            raise Http404("No tenant found for this request")

        # Superuser bypass
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)

        # Check for admin role
        roles = get_user_roles(request.user, request.school)
        if "admin" in roles:
            return view_func(request, *args, **kwargs)

        return HttpResponseForbidden("You do not have permission to access this page.")

    return wrapper


def admin_or_teacher_required(view_func):
    """Require user to be an admin or teacher in the current school"""

    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not getattr(request, "school", None):
            raise Http404("No tenant found for this request")

        # Superuser bypass
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)

        # Check for admin or teacher role
        roles = get_user_roles(request.user, request.school)
        if "admin" in roles or "teacher" in roles:
            return view_func(request, *args, **kwargs)

        return HttpResponseForbidden("You do not have permission to access this page.")

    return wrapper


def role_required(*allowed_roles):
    """
    Require user to have one of the specified roles.

    Usage:
        @role_required("admin", "teacher")
        def my_view(request):
            ...
    """

    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            if not getattr(request, "school", None):
                raise Http404("No tenant found for this request")

            # Superuser bypass
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            # Check for allowed roles
            roles = get_user_roles(request.user, request.school)
            if any(role in roles for role in allowed_roles):
                return view_func(request, *args, **kwargs)

            return HttpResponseForbidden("You do not have permission to access this page.")

        return wrapper

    return decorator
