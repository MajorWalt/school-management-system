from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.models import UserRole
from .forms import BehaviourIncidentForm
from .models import BehaviourIncident
from .services import create_incident, delete_incident, update_incident


def check_admin_only(request):
    """Check if user is admin. Returns HttpResponseForbidden if not."""
    if request.user.is_superuser:
        return None

    roles = list(UserRole.objects.filter(user=request.user, school=request.school).values_list("role", flat=True))
    if "admin" not in roles:
        return HttpResponseForbidden("You do not have permission to access this page.")
    return None
    pass


def incident_list(request):
    """List all behaviour incidents with filtering and pagination."""
    admin_check = check_admin_only(request)
    if admin_check:
        return admin_check

    # Get all incidents for this school
    incidents = BehaviourIncident.objects.filter(school=request.school).select_related(
        "student", "student__homeroom", "student__homeroom__form", "logged_by", "academic_year"
    )

    # Filter by search query (student name)
    query = request.GET.get("q", "").strip()
    if query:
        words = query.split()
        q_filter = Q()
        for word in words:
            q_filter &= Q(student__first_name__icontains=word) | Q(student__last_name__icontains=word)
        incidents = incidents.filter(q_filter)

    # Filter by incident type
    incident_type = request.GET.get("type", "").strip()
    if incident_type in ["detention", "suspension"]:
        incidents = incidents.filter(incident_type=incident_type)

    # Filter by form (get forms from current incidents in school)
    form_filter = request.GET.get("form", "").strip()
    if form_filter:
        incidents = incidents.filter(student__homeroom__form__name=form_filter)

    # Filter by academic year
    year_filter = request.GET.get("year", "").strip()
    if year_filter:
        incidents = incidents.filter(academic_year__name=year_filter)

    # Filter by date range
    date_from = request.GET.get("date_from", "").strip()
    date_to = request.GET.get("date_to", "").strip()
    try:
        if date_from:
            from_date = timezone.datetime.strptime(date_from, "%Y-%m-%d").date()
            incidents = incidents.filter(incident_date__gte=from_date)
    except (ValueError, TypeError):
        pass
    try:
        if date_to:
            to_date = timezone.datetime.strptime(date_to, "%Y-%m-%d").date()
            incidents = incidents.filter(incident_date__lte=to_date)
    except (ValueError, TypeError):
        pass

    # Get unique forms and years present in this school's incidents
    school_incidents = BehaviourIncident.objects.filter(school=request.school)
    available_forms = sorted(set(school_incidents.filter(student__homeroom__form__isnull=False).values_list("student__homeroom__form__name", flat=True)))
    available_years = sorted(
        set(school_incidents.values_list("academic_year__name", flat=True)),
        reverse=True,
    )

    # Paginate
    paginator = Paginator(incidents, 25)
    page_num = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_num)

    # Build querystring for pagination links
    querystring = ""
    if query:
        querystring += f"&q={query}"
    if incident_type:
        querystring += f"&type={incident_type}"
    if form_filter:
        querystring += f"&form={form_filter}"
    if year_filter:
        querystring += f"&year={year_filter}"
    if date_from:
        querystring += f"&date_from={date_from}"
    if date_to:
        querystring += f"&date_to={date_to}"

    return render(
        request,
        "behaviour/incident_list.html",
        {
            "page_obj": page_obj,
            "querystring": querystring,
            "query": query,
            "incident_type": incident_type,
            "form_filter": form_filter,
            "year_filter": year_filter,
            "date_from": date_from,
            "date_to": date_to,
            "available_forms": available_forms,
            "available_years": available_years,
            "has_filters": bool(query or incident_type or form_filter or year_filter or date_from or date_to),
        },
    )
    pass


def incident_create(request):
    """Create a new behaviour incident."""
    admin_check = check_admin_only(request)
    if admin_check:
        return admin_check

    # Optional student prefill
    initial_data = {}
    if request.method == "GET":
        student_id = request.GET.get("student")
        if student_id:
            try:
                from students.models import Student

                student = get_object_or_404(Student, pk=int(student_id), school=request.school)
                initial_data["student"] = student
            except (ValueError, TypeError):
                pass

    form = BehaviourIncidentForm(request.POST or None, school=request.school, initial=initial_data)

    if request.method == "POST" and form.is_valid():
        incident = create_incident(form, request)
        messages.success(request, f"Behaviour incident created for {incident.student.get_full_name()}.")
        return redirect("behaviour:incident_detail", pk=incident.pk)

    return render(
        request,
        "behaviour/incident_form.html",
        {
            "form": form,
            "title": "Log Behaviour Incident",
            "is_create": True,
            "alpine_state": form.alpine_state(),
        },
    )
    pass


def incident_detail(request, pk):
    """View details of a behaviour incident."""
    admin_check = check_admin_only(request)
    if admin_check:
        return admin_check

    incident = get_object_or_404(BehaviourIncident, pk=pk, school=request.school)

    return render(
        request,
        "behaviour/incident_detail.html",
        {
            "incident": incident,
        },
    )
    pass


def incident_edit(request, pk):
    """Edit an existing behaviour incident."""
    admin_check = check_admin_only(request)
    if admin_check:
        return admin_check

    incident = get_object_or_404(BehaviourIncident, pk=pk, school=request.school)
    form = BehaviourIncidentForm(request.POST or None, school=request.school, instance=incident)

    if request.method == "POST" and form.is_valid():
        update_incident(form, request)
        messages.success(request, f"Behaviour incident updated for {incident.student.get_full_name()}.")
        return redirect("behaviour:incident_detail", pk=incident.pk)

    return render(
        request,
        "behaviour/incident_form.html",
        {
            "form": form,
            "title": "Edit Behaviour Incident",
            "is_create": False,
            "incident": incident,
            "alpine_state": form.alpine_state(),
        },
    )
    pass


def incident_delete(request, pk):
    """Delete a behaviour incident (GET shows confirm, POST performs delete)."""
    admin_check = check_admin_only(request)
    if admin_check:
        return admin_check

    incident = get_object_or_404(BehaviourIncident, pk=pk, school=request.school)

    if request.method == "POST":
        student_name = incident.student.get_full_name()
        delete_incident(incident, request)
        messages.warning(request, f"Behaviour incident for {student_name} has been deleted.")
        return redirect("behaviour:incident_list")

    return render(
        request,
        "behaviour/incident_delete.html",
        {
            "incident": incident,
        },
    )
    pass
