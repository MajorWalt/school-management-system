from django import forms
from .models import AcademicYear, Course, Enrolment, FormTermRule, NonSchoolDay, Section, TermConfig

FIELD_CLASS = (
	"w-full rounded-lg border border-gray-300 px-3 py-2 text-sm "
	"focus:outline-none focus:ring-2 focus:ring-blue-500"
)


def apply_classes(form):
	for field in form.fields.values():
		existing = field.widget.attrs.get("class", "")
		field.widget.attrs["class"] = FIELD_CLASS + " " + existing


class AcademicYearForm(forms.ModelForm):

	class Meta:
		model  = AcademicYear
		fields = ["name", "is_current"]

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		apply_classes(self)


class TermConfigForm(forms.ModelForm):

	class Meta:
		model  = TermConfig
		fields = ["term_number", "name", "has_final_exam", "coursework_weight", "exam_weight"]

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		apply_classes(self)


class FormTermRuleForm(forms.ModelForm):

	class Meta:
		model  = FormTermRule
		fields = ["form", "term_number", "exam_label", "exam_replaces_final", "notes"]
		widgets = {"notes": forms.Textarea(attrs={"rows": 2})}

	def __init__(self, *args, school=None, **kwargs):
		super().__init__(*args, **kwargs)
		if school:
			self.fields["form"].queryset = self.fields["form"].queryset.filter(school=school)
		apply_classes(self)


class NonSchoolDayForm(forms.ModelForm):

	class Meta:
		model  = NonSchoolDay
		fields = ["date", "label", "type"]
		widgets = {"date": forms.DateInput(attrs={"type": "date"})}

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		apply_classes(self)


class CourseForm(forms.ModelForm):

	class Meta:
		model  = Course
		fields = ["name", "code", "active"]

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		apply_classes(self)


class SectionForm(forms.ModelForm):

	class Meta:
		model  = Section
		fields = ["course", "academic_year", "term_number", "form", "teacher", "room"]

	def __init__(self, *args, school=None, **kwargs):
		super().__init__(*args, **kwargs)
		if school:
			self.fields["course"].queryset        = self.fields["course"].queryset.filter(school=school)
			self.fields["academic_year"].queryset = self.fields["academic_year"].queryset.filter(school=school)
			self.fields["form"].queryset          = self.fields["form"].queryset.filter(school=school)
			self.fields["teacher"].queryset       = self.fields["teacher"].queryset.filter(school=school, active=True)
		apply_classes(self)


class EnrolmentForm(forms.ModelForm):

	class Meta:
		model  = Enrolment
		fields = ["student", "section"]

	def __init__(self, *args, school=None, **kwargs):
		super().__init__(*args, **kwargs)
		if school:
			self.fields["student"].queryset = self.fields["student"].queryset.filter(school=school)
			self.fields["section"].queryset = self.fields["section"].queryset.filter(school=school)
		apply_classes(self)