from django import forms
from .models import DemeritRecord, MeritRecord

FIELD_CLASS = (
	"w-full rounded-lg border border-gray-300 px-3 py-2 text-sm "
	"focus:outline-none focus:ring-2 focus:ring-blue-500"
)


class MeritForm(forms.ModelForm):

	class Meta:
		model   = MeritRecord
		fields  = ["student", "awarded_by", "category", "reason", "count", "date"]
		widgets = {
			"date":   forms.DateInput(attrs={"type": "date"}),
			"reason": forms.Textarea(attrs={"rows": 2}),
		}

	def __init__(self, *args, school=None, **kwargs):
		super().__init__(*args, **kwargs)
		if school:
			self.fields["student"].queryset    = self.fields["student"].queryset.filter(school=school)
			self.fields["awarded_by"].queryset = self.fields["awarded_by"].queryset.filter(school=school, active=True)
		self.fields["count"].label = "Merits"
		for field in self.fields.values():
			existing = field.widget.attrs.get("class", "")
			field.widget.attrs["class"] = FIELD_CLASS + " " + existing


class DemeritForm(forms.ModelForm):

	class Meta:
		model   = DemeritRecord
		fields  = ["student", "awarded_by", "category", "reason", "count", "date"]
		widgets = {
			"date":   forms.DateInput(attrs={"type": "date"}),
			"reason": forms.Textarea(attrs={"rows": 2}),
		}

	def __init__(self, *args, school=None, **kwargs):
		super().__init__(*args, **kwargs)
		if school:
			self.fields["student"].queryset    = self.fields["student"].queryset.filter(school=school)
			self.fields["awarded_by"].queryset = self.fields["awarded_by"].queryset.filter(school=school, active=True)
		self.fields["count"].label = "Demerits"
		for field in self.fields.values():
			existing = field.widget.attrs.get("class", "")
			field.widget.attrs["class"] = FIELD_CLASS + " " + existing