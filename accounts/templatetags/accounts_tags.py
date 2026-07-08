from django import template
from accounts.models import UserRole

register = template.Library()


@register.simple_tag
def get_roles(user, school):
    """Get all roles for a user in a school"""
    if not user or not school:
        return []
    return list(UserRole.objects.filter(user=user, school=school).values_list("role", flat=True))


@register.simple_tag
def is_admin(user, school):
    """Check if user is admin in the school"""
    if not user or not school:
        return False
    if user.is_superuser:
        return True
    return UserRole.objects.filter(user=user, school=school, role="admin").exists()


@register.simple_tag
def is_teacher(user, school):
    """Check if user is teacher in the school"""
    if not user or not school:
        return False
    if user.is_superuser:
        return True
    return UserRole.objects.filter(user=user, school=school, role="teacher").exists()


@register.simple_tag
def is_student(user, school):
    """Check if user is student in the school"""
    if not user or not school:
        return False
    if user.is_superuser:
        return True
    return UserRole.objects.filter(user=user, school=school, role="student").exists()


@register.simple_tag
def is_admin_or_teacher(user, school):
    """Check if user is admin or teacher in the school"""
    if not user or not school:
        return False
    if user.is_superuser:
        return True
    roles = UserRole.objects.filter(user=user, school=school).values_list("role", flat=True)
    return "admin" in roles or "teacher" in roles


@register.simple_tag
def has_role(user, school, role):
    """Check if user has a specific role in the school"""
    if not user or not school or not role:
        return False
    if user.is_superuser:
        return True
    return UserRole.objects.filter(user=user, school=school, role=role).exists()


@register.filter
def split(value, delimiter=","):
    """Split a string by delimiter"""
    return value.split(delimiter)


@register.filter
def get_item(dictionary, key):
    """Get item from dictionary"""
    return dictionary.get(key)
