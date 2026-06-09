from django import forms
from .models import Guardian, House, Student, StudentGuardian, StudentStatusLog

FIELD_CLASS = (
	"w-full rounded-lg border border-gray-300 px-3 py-2 text-sm "
	"focus:outline-none focus:ring-2 focus:ring-blue-500"
)


class StudentForm(forms.ModelForm):

	class Meta:
		model  = Student
		fields = [
			# Core
			"student_id", "first_name", "middle_name", "last_name",
			"gender", "date_of_birth", "nationality", "religion", "house",
			# Contact
			"phone", "email", "address", "city", "parish", "community",
			# Academic
			"form", "homeroom", "admission_date", "previous_school", "photo",
			# IDs
			"emis_id", "csec_candidate_no",
			# Cohort
			"cohort_grade", "cohort_year", "repeated",
			# GSNA
			"gsna_year", "gsna_award", "gsna_english", "gsna_mathematics",
			"gsna_science", "gsna_social_studies",
			# Graduation
			"grad_date", "sponsor",
			# Birth parents
			"father_name", "mother_name",
			# Emergency
			"emergency_contact_name", "emergency_relation",
			"emergency_phone_1", "emergency_phone_2",
			"emergency_work_phone", "emergency_workplace",
			# Doctor
			"doctor_name", "doctor_phone",
			# Restrictions
			"restrict_contact_1", "restrict_contact_2", "lives_with",
			# Notes
			"notes",
		]
		widgets = {
			"date_of_birth":  forms.DateInput(attrs={"type": "date"}),
			"admission_date": forms.DateInput(attrs={"type": "date"}),
			"grad_date":      forms.DateInput(attrs={"type": "date"}),
			"address":        forms.Textarea(attrs={"rows": 2}),
			"notes":          forms.Textarea(attrs={"rows": 3}),
		}

	def __init__(self, *args, school=None, **kwargs):
		super().__init__(*args, **kwargs)
		if school:
			self.fields["form"].queryset     = self.fields["form"].queryset.filter(school=school)
			self.fields["homeroom"].queryset = self.fields["homeroom"].queryset.filter(school=school)
			self.fields["house"].queryset    = self.fields["house"].queryset.filter(school=school)
		for field in self.fields.values():
			existing = field.widget.attrs.get("class", "")
			if not isinstance(field.widget, forms.CheckboxInput):
				field.widget.attrs["class"] = FIELD_CLASS + " " + existing


class BulkEnrolForm(forms.Form):
    excel_file = forms.FileField(
        label="Excel File (.xlsx)",
        help_text="Download the template, fill it in, then upload here."
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["excel_file"].widget.attrs["class"]  = FIELD_CLASS
        self.fields["excel_file"].widget.attrs["accept"] = ".xlsx"


class GuardianForm(forms.ModelForm):

	class Meta:
		model  = Guardian
		fields = ["first_name", "last_name", "phone", "email", "address"]
		widgets = {
			"address": forms.Textarea(attrs={"rows": 2}),
		}

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		for field in self.fields.values():
			field.widget.attrs["class"] = FIELD_CLASS


class StudentGuardianForm(forms.ModelForm):

	class Meta:
		model  = StudentGuardian
		fields = ["guardian", "relationship", "is_primary", "can_pickup"]

	def __init__(self, *args, school=None, **kwargs):
		super().__init__(*args, **kwargs)
		if school:
			self.fields["guardian"].queryset = Guardian.objects.filter(school=school)
		for name, field in self.fields.items():
			if name not in ("is_primary", "can_pickup"):
				field.widget.attrs["class"] = FIELD_CLASS


class StudentStatusForm(forms.ModelForm):

	class Meta:
		model  = StudentStatusLog
		fields = ["status", "change_date", "reason"]
		widgets = {
			"change_date": forms.DateInput(attrs={"type": "date"}),
			"reason":      forms.Textarea(attrs={"rows": 2}),
		}

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		for field in self.fields.values():
			existing = field.widget.attrs.get("class", "")
			field.widget.attrs["class"] = FIELD_CLASS + " " + existing