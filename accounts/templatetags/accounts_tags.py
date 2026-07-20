from django import template
from accounts.utils import (
    get_roles as check_get_roles,
    is_admin as check_is_admin,
    is_teacher as check_is_teacher,
    is_student as check_is_student,
    is_admin_or_teacher as check_is_admin_or_teacher,
    has_role as check_has_role,
)

register = template.Library()


@register.simple_tag
def get_roles(user, school):
    """Get all roles for a user in a school"""
    return check_get_roles(user, school)


@register.simple_tag
def is_admin(user, school):
    """Check if user is admin in the school"""
    return check_is_admin(user, school)


@register.simple_tag
def is_teacher(user, school):
    """Check if user is teacher in the school"""
    return check_is_teacher(user, school)


@register.simple_tag
def is_student(user, school):
    """Check if user is student in the school"""
    return check_is_student(user, school)


@register.simple_tag
def is_admin_or_teacher(user, school):
    """Check if user is admin or teacher in the school"""
    return check_is_admin_or_teacher(user, school)


@register.simple_tag
def has_role(user, school, role):
    """Check if user has a specific role in the school"""
    return check_has_role(user, school, role)


@register.filter
def split(value, delimiter=","):
    """Split a string by delimiter"""
    return value.split(delimiter)


@register.filter
def get_item(dictionary, key):
    """Get item from dictionary"""
    return dictionary.get(key)
