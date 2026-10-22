from django import forms
from django.forms import inlineformset_factory

from scheduling.models import Course
from .models import CriteriaRequirement, PromotionCriteria

FIELD_CLASS = "w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"


def _style(form):
    for field in form.fields.values():
        if isinstance(field.widget, (forms.CheckboxInput, forms.CheckboxSelectMultiple, forms.HiddenInput)):
            continue
        existing = field.widget.attrs.get("class", "")
        field.widget.attrs["class"] = f"{FIELD_CLASS} {existing}".strip()


class PromotionCriteriaForm(forms.ModelForm):
    class Meta:
        model = PromotionCriteria
        fields = ["outcome", "pass_mark", "min_overall_average", "max_failed_subjects", "active", "notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self)

    def clean_pass_mark(self):
        v = self.cleaned_data["pass_mark"]
        if v > 100:
            raise forms.ValidationError("Pass mark cannot be more than 100.")
        return v

    def clean_min_overall_average(self):
        v = self.cleaned_data.get("min_overall_average")
        if v is not None and (v < 0 or v > 100):
            raise forms.ValidationError("Enter a value between 0 and 100.")
        return v


class CriteriaRequirementForm(forms.ModelForm):
    subject_areas = forms.MultipleChoiceField(
        choices=Course.SUBJECT_AREA_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )

    class Meta:
        model = CriteriaRequirement
        fields = ["label", "subject_areas", "min_to_pass", "order"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["label"].widget.attrs["placeholder"] = "e.g. One foreign language"
        _style(self)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("DELETE"):
            return cleaned
        label = (cleaned.get("label") or "").strip()
        areas = cleaned.get("subject_areas") or []
        min_to_pass = cleaned.get("min_to_pass") or 0
        if not label and not areas:
            return cleaned
        if not label:
            self.add_error("label", "Give this requirement a name.")
        if not areas:
            self.add_error("subject_areas", "Tick at least one subject.")
        if min_to_pass < 1:
            self.add_error("min_to_pass", "Must be at least 1.")
        elif areas and min_to_pass > len(areas):
            self.add_error("min_to_pass", f"Cannot be more than the {len(areas)} subject(s) ticked.")
        return cleaned


RequirementFormSet = inlineformset_factory(
    PromotionCriteria,
    CriteriaRequirement,
    form=CriteriaRequirementForm,
    extra=3,
    can_delete=True,
)