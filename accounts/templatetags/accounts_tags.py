from django import template
from accounts.models import UserRole

register = template.Library()


@register.simple_tag
def get_roles(user, school):
    if not user or not school:
        return []
    return list(UserRole.objects.filter(user=user, school=school).values_list("role", flat=True))


@register.filter
def split(value, delimiter=","):
    return value.split(delimiter)


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)
