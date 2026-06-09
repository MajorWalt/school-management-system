from django import forms
from .models import Evaluation, GradeEntry, GradeVisibilityRule, GradeWindow

FIELD_CLASS = (
	"w-full rounded-lg border border-gray-300 px-3 py-2 text-sm "
	"focus:outline-none focus:ring-2 focus:ring-blue-500"
)


class EvaluationForm(forms.ModelForm):

	class Meta:
		model  = Evaluation
		fields = ["title", "category", "subcategory", "max_marks", "weight", "is_final_exam", "date"]
		widgets = {
			"date": forms.DateInput(attrs={"type": "date"}),
		}

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		for field in self.fields.values():
			if not isinstance(field.widget, forms.CheckboxInput):
				existing = field.widget.attrs.get("class", "")
				field.widget.attrs["class"] = FIELD_CLASS + " " + existing


class GradeVisibilityForm(forms.ModelForm):

	class Meta:
		model   = GradeVisibilityRule
		fields  = ["is_visible", "reason"]
		widgets = {"reason": forms.Textarea(attrs={"rows": 2})}

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		for field in self.fields.values():
			existing = field.widget.attrs.get("class", "")
			field.widget.attrs["class"] = FIELD_CLASS + " " + existing


class BulkGradeUploadForm(forms.Form):
	excel_file = forms.FileField(
		label="Excel File (.xlsx)",
		help_text="Download the template, fill in grades, then upload."
	)

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.fields["excel_file"].widget.attrs["class"]  = FIELD_CLASS
		self.fields["excel_file"].widget.attrs["accept"] = ".xlsx"