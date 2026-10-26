from accounts.models import UserRole
from staff.models import Staff


def tenant(request):
    return {
        "school": getattr(request, "school", None),
        "school_profile": getattr(request, "school_profile", None),
    }
    pass


def user_roles(request):
    """
    Add user role information to all templates.
    Provides: is_admin, is_teacher, is_student, user_roles, is_admin_or_teacher, is_homeroom_teacher
    """
    if not hasattr(request, 'user') or not request.user.is_authenticated or not hasattr(request, "school"):
        return {
            "is_admin": False,
            "is_teacher": False,
            "is_student": False,
            "user_roles": [],
            "is_admin_or_teacher": False,
            "is_homeroom_teacher": False,
        }

    school = getattr(request, "school", None)
    if not school:
        return {
            "is_admin": False,
            "is_teacher": False,
            "is_student": False,
            "user_roles": [],
            "is_admin_or_teacher": False,
            "is_homeroom_teacher": False,
        }

    # Superuser bypass
    if request.user.is_superuser:
        return {
            "is_admin": True,
            "is_teacher": True,
            "is_student": False,
            "user_roles": ["admin", "teacher"],
            "is_admin_or_teacher": True,
            "is_homeroom_teacher": False,
        }

    # Get user roles
    role_list = list(UserRole.objects.filter(user=request.user, school=school).values_list("role", flat=True))

    is_teacher = "teacher" in role_list
    is_homeroom_teacher = False
    if is_teacher:
        is_homeroom_teacher = Staff.objects.filter(
            user=request.user, school=school, homeroom__isnull=False
        ).exists()

    return {
        "is_admin": "admin" in role_list,
        "is_teacher": is_teacher,
        "is_student": "student" in role_list,
        "user_roles": role_list,
        "is_admin_or_teacher": "admin" in role_list or is_teacher,
        "is_homeroom_teacher": is_homeroom_teacher,
    }
    pass