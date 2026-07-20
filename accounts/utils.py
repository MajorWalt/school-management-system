"""
Centralized utility functions for user role and permission checking.
Consolidates role checking logic that was previously duplicated across multiple modules.
"""

from accounts.models import UserRole


def get_roles(user, school):
    """Get all roles for a user in a school"""
    if not user or not school:
        return []
    return list(UserRole.objects.filter(user=user, school=school).values_list("role", flat=True))


def is_admin(user, school):
    """Check if user is admin in the school"""
    if not user or not school:
        return False
    if user.is_superuser:
        return True
    return UserRole.objects.filter(user=user, school=school, role="admin").exists()


def is_teacher(user, school):
    """Check if user is teacher in the school"""
    if not user or not school:
        return False
    if user.is_superuser:
        return True
    return UserRole.objects.filter(user=user, school=school, role="teacher").exists()


def is_student(user, school):
    """Check if user is student in the school"""
    if not user or not school:
        return False
    if user.is_superuser:
        return True
    return UserRole.objects.filter(user=user, school=school, role="student").exists()


def is_admin_or_teacher(user, school):
    """Check if user is admin or teacher in the school"""
    if not user or not school:
        return False
    if user.is_superuser:
        return True
    roles = UserRole.objects.filter(user=user, school=school).values_list("role", flat=True)
    return "admin" in roles or "teacher" in roles


def has_role(user, school, role):
    """Check if user has a specific role in the school"""
    if not user or not school or not role:
        return False
    if user.is_superuser:
        return True
    return UserRole.objects.filter(user=user, school=school, role=role).exists()
