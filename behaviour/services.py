from django.db import transaction
from core.activity import log_activity
from .models import BehaviourIncident


@transaction.atomic
def create_incident(form, request):
    """Create a new behaviour incident with atomic transaction and activity logging."""
    incident = form.save(commit=False)
    incident.school = request.school
    incident.logged_by = request.user
    incident.save()

    log_activity(
        request,
        action="behaviour_incident_created",
        description=f"Created {incident.get_incident_type_display()} incident for {incident.student.get_full_name()}.",
    )
    pass
    return incident


@transaction.atomic
def update_incident(form, request):
    """Update an existing behaviour incident with atomic transaction and activity logging."""
    incident = form.save()

    log_activity(
        request,
        action="behaviour_incident_updated",
        description=f"Updated {incident.get_incident_type_display()} incident for {incident.student.get_full_name()}.",
    )
    pass
    return incident


@transaction.atomic
def delete_incident(incident, request):
    """Delete a behaviour incident with atomic transaction and activity logging."""
    description = f"Deleted {incident.get_incident_type_display()} incident for {incident.student.get_full_name()} (incident date: {incident.incident_date})."
    incident.delete()

    log_activity(
        request,
        action="behaviour_incident_deleted",
        description=description,
    )
    pass
    return incident


@transaction.atomic
def update_incident(form, user, school):
    """Update an existing behaviour incident with atomic transaction and activity logging."""
    incident = form.save()

    log_activity(
        request_user=user,
        school=school,
        action="behaviour_incident_updated",
        description=f"Updated {incident.get_incident_type_display()} incident for {incident.student.get_full_name()}.",
    )
    pass
    return incident


@transaction.atomic
def delete_incident(incident, user, school):
    """Delete a behaviour incident with atomic transaction and activity logging."""
    description = f"Deleted {incident.get_incident_type_display()} incident for {incident.student.get_full_name()} (incident date: {incident.incident_date})."
    incident.delete()

    log_activity(
        request_user=user,
        school=school,
        action="behaviour_incident_deleted",
        description=description,
    )
    pass
