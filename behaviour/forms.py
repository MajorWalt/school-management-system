import json
from django import forms
from django.utils import timezone
from .models import BehaviourIncident, INCIDENT_TYPE_CHOICES

FIELD_CLASS = "w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"


class BehaviourIncidentForm(forms.ModelForm):
    class Meta:
        model = BehaviourIncident
        fields = [
            "incident_type",
            "student",
            "academic_year",
            "incident_date",
            "term_number",
            "reason",
            # Suspension fields
            "start_date",
            "end_date",
            "suspension_type",
        ]
        widgets = {
            "incident_date": forms.DateInput(attrs={"type": "date", "format": "%Y-%m-%d"}),
            "reason": forms.Textarea(attrs={"rows": 4}),
            "start_date": forms.DateInput(attrs={"type": "date", "format": "%Y-%m-%d"}),
            "end_date": forms.DateInput(attrs={"type": "date", "format": "%Y-%m-%d"}),
        }

    def __init__(self, *args, school=None, **kwargs):
        super().__init__(*args, **kwargs)

        # Set all type-specific fields to not required (will validate in clean)
        for field_name in [
            "start_date",
            "end_date",
            "suspension_type",
        ]:
            self.fields[field_name].required = False

        # Filter querysets to school
        if school:
            self.fields["student"].queryset = self.fields["student"].queryset.filter(school=school).order_by("last_name", "first_name")
            self.fields["academic_year"].queryset = self.fields["academic_year"].queryset.filter(school=school)

        # Set default academic year to current
        if school and not self.instance.pk:
            try:
                current_year = school.academic_years.filter(is_current=True).first()
                if current_year:
                    self.fields["academic_year"].initial = current_year
            except Exception:
                pass

        # Lock incident_type on edit
        if self.instance.pk:
            self.fields["incident_type"].disabled = True

        # Apply Tailwind styling
        for field_name, field in self.fields.items():
            if field_name not in ["incident_type"]:
                existing = field.widget.attrs.get("class", "")
                field.widget.attrs["class"] = FIELD_CLASS + " " + existing

    def alpine_state(self):
        """Return JSON state for Alpine.js x-data initialization."""
        # Use form data if available (POST with errors), otherwise use instance or initial
        if self.data:
            incident_type = self.data.get("incident_type", "detention")
            start_date = self.data.get("start_date", "")
        elif self.instance and self.instance.pk:
            # Edit mode - use saved instance values
            incident_type = self.instance.incident_type
            start_date = self.instance.start_date.isoformat() if self.instance.start_date else ""
        else:
            # Create mode - use form initial values
            incident_type = self.initial.get("incident_type", "detention")
            start_date = self.initial.get("start_date", "")
            if hasattr(start_date, "isoformat"):
                start_date = start_date.isoformat()

        return json.dumps(
            {
                "type": incident_type,
                "startDate": start_date,
            }
        )
        pass

    def clean(self):
        """Validate form."""
        cleaned_data = super().clean()
        incident_type = cleaned_data.get("incident_type")

        # Suspension validation
        if incident_type == "suspension":
            if not cleaned_data.get("start_date"):
                self.add_error("start_date", "Start date is required.")
            if not cleaned_data.get("end_date"):
                self.add_error("end_date", "End date is required.")
            if not cleaned_data.get("suspension_type"):
                self.add_error("suspension_type", "Suspension type is required.")

        return cleaned_data
        pass
