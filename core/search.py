from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import render
from django.urls import NoReverseMatch, reverse
from django.views.decorators.http import require_GET
from watson import search as watson

from core.constants import DEPARTMENT_CHOICES
from staff.models import Staff
from students.models import Student

RESULT_LIMIT = 8
MAX_QUERY_LENGTH = 64

# Adjust to match your model fields / URL names if they differ.
STUDENT_SUBTITLE_FIELD = "student_id"
STAFF_DEPARTMENT_FIELDS = ("department", "department_2")
STUDENT_DETAIL_URL = "students:detail"
STAFF_DETAIL_URL = "staff:detail"

DEPARTMENT_LABELS = dict(DEPARTMENT_CHOICES)


def _safe_reverse(name, pk):
    try:
        return reverse(name, args=[pk])
    except NoReverseMatch:
        return ""
    pass


def _initials(name):
    parts = [p for p in name.split() if p]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:1].upper()
    return (parts[0][:1] + parts[-1][:1]).upper()
    pass


def _get_staff(request):
    return (
        Staff.objects.filter(school=request.school, user=request.user)
        .select_related("user")
        .first()
    )
    pass


def _is_admin(request, staff):
    # Mirror the is_admin check used by the sidebar context processor.
    return request.user.is_superuser
    pass


def _staff_departments(staff):
    return [
        getattr(staff, field)
        for field in STAFF_DEPARTMENT_FIELDS
        if getattr(staff, field, None)
    ]
    pass


def _department_query(departments):
    query = Q()
    for field in STAFF_DEPARTMENT_FIELDS:
        query |= Q(**{f"{field}__in": departments})
    return query
    pass


def _student_items(request, query):
    queryset = Student.objects.filter(school=request.school)
    students = watson.filter(queryset, query)[:RESULT_LIMIT]

    items = []
    for student in students:
        name = f"{student.first_name} {student.last_name}".strip()
        items.append(
            {
                "kind": "student",
                "name": name,
                "subtitle": getattr(student, STUDENT_SUBTITLE_FIELD, "") or "",
                "initials": _initials(name),
                "url": _safe_reverse(STUDENT_DETAIL_URL, student.pk),
            }
        )
    return items
    pass


def _staff_items(request, query, departments=None, exclude_pk=None):
    queryset = Staff.objects.filter(
        school=request.school, user__is_active=True
    ).select_related("user")
    if departments is not None:
        queryset = queryset.filter(_department_query(departments))
    if exclude_pk is not None:
        queryset = queryset.exclude(pk=exclude_pk)

    members = watson.filter(queryset, query)[:RESULT_LIMIT]

    items = []
    for member in members:
        name = member.user.get_full_name() or member.user.email
        dept_labels = [
            DEPARTMENT_LABELS.get(value, value) for value in _staff_departments(member)
        ]
        items.append(
            {
                "kind": "staff",
                "name": name,
                "subtitle": " · ".join(dept_labels) or member.user.email,
                "initials": _initials(name),
                "url": _safe_reverse(STAFF_DETAIL_URL, member.pk),
            }
        )
    return items
    pass


@login_required
@require_GET
def global_search(request):
    staff = _get_staff(request)
    is_admin = _is_admin(request, staff)

    if not is_admin and staff is None:
        return HttpResponseForbidden()

    query = request.GET.get("q", "").strip()[:MAX_QUERY_LENGTH]
    groups = []

    if query:
        students = _student_items(request, query)
        if students:
            groups.append({"label": "Students", "items": students})

        if is_admin:
            staff_items = _staff_items(request, query)
        elif staff.is_head_of_department and _staff_departments(staff):
            staff_items = _staff_items(
                request,
                query,
                departments=_staff_departments(staff),
                exclude_pk=staff.pk,
            )
        else:
            staff_items = []

        if staff_items:
            groups.append({"label": "Staff", "items": staff_items})

    return render(
        request,
        "core/partials/global_search_results.html",
        {"query": query, "groups": groups},
    )
    pass