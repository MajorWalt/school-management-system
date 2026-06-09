from django import forms
from .models import GradeEntry, GradeVisibilityRule

FIELD_CLASS = (
	"w-full rounded-lg border border-gray-300 px-3 py-2 text-sm "
	"focus:outline-none focus:ring-2 focus:ring-blue-500"
)


class GradeEntryForm(forms.ModelForm):

	class Meta:
		model  = GradeEntry
		fields = ["category", "title", "max_marks", "marks_earned", "weight", "is_final_exam", "date", "note"]
		widgets = {
			"date": forms.DateInput(attrs={"type": "date"}),
			"note": forms.Textarea(attrs={"rows": 2}),
		}

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		for field in self.fields.values():
			existing = field.widget.attrs.get("class", "")
			field.widget.attrs["class"] = FIELD_CLASS + " " + existing


class GradeVisibilityForm(forms.ModelForm):

	class Meta:
		model  = GradeVisibilityRule
		fields = ["is_visible", "reason"]
		widgets = {
			"reason": forms.Textarea(attrs={"rows": 2}),
		}

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		for field in self.fields.values():
			existing = field.widget.attrs.get("class", "")
			field.widget.attrs["class"] = FIELD_CLASS + " " + existing