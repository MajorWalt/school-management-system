from django import forms
from .models import Staff

FIELD_CLASS = "w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"


class StaffForm(forms.ModelForm):
    class Meta:
        model = Staff
        fields = [
            # Identity
            "employee_number",
            "salutation",
            "first_name",
            "middle_name",
            "last_name",
            "gender",
            "date_of_birth",
            "nationality",
            "social_security_no",
            "house",
            "emis_id",
            # Contact
            "phone_1",
            "phone_2",
            "phone_3",
            "email_work",
            "email_personal",
            "email_emis",
            "address",
            "city",
            "parish",
            # Employment
            "department",
            "department_2",
            "is_head_of_department",
            "role_title",
            "subject_specialisation",
            "hire_date",
            "end_date",
            "does_attendance",
            "active",
            "homeroom",
            # Emergency
            "emergency_contact_name",
            "emergency_contact_phone",
            "emergency_contact_relation",
            # MoE
            "teacher_type",
            "date_started_teaching",
            "date_appointed",
            "previous_schools",
            "highest_degree",
            "degree_specification",
        ]
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
            "hire_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "date_started_teaching": forms.DateInput(attrs={"type": "date"}),
            "date_appointed": forms.DateInput(attrs={"type": "date"}),
            "address": forms.Textarea(attrs={"rows": 2}),
            "previous_schools": forms.Textarea(attrs={"rows": 2}),
            "degree_specification": forms.Textarea(attrs={"rows": 2}),
            # Second department can only be picked once a primary department exists.
            "department_2": forms.Select(attrs={"x-bind:disabled": "!hasDept"}),
            # HOD is disabled (and force-unchecked) until a department is chosen.
            "is_head_of_department": forms.CheckboxInput(attrs={
                "x-bind:disabled": "!hasDept",
                "x-effect": "if (!hasDept) $el.checked = false",
            }),
        }

    def __init__(self, *args, school=None, **kwargs):
        super().__init__(*args, **kwargs)
        if school:
            self.fields["homeroom"].queryset = self.fields["homeroom"].queryset.filter(school=school)
        for name, field in self.fields.items():
            if not isinstance(field.widget, forms.CheckboxInput):
                existing = field.widget.attrs.get("class", "")
                field.widget.attrs["class"] = FIELD_CLASS + " " + existing
        pass