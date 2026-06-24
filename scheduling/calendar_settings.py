from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.forms import modelformset_factory
from django.shortcuts import render, redirect
from django.urls import reverse

from .models import AcademicYear, TermConfig
from attendance.utils import get_active_academic_year


_DATE_CLASS = "mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"


class AcademicYearDatesForm(forms.ModelForm):

	class Meta:
		model  = AcademicYear
		fields = ["start_date", "end_date"]
		widgets = {
			"start_date": forms.DateInput(attrs={"type": "date", "class": _DATE_CLASS}, format="%Y-%m-%d"),
			"end_date":   forms.DateInput(attrs={"type": "date", "class": _DATE_CLASS}, format="%Y-%m-%d"),
		}
		pass

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.fields["start_date"].input_formats = ["%Y-%m-%d"]
		self.fields["end_date"].input_formats   = ["%Y-%m-%d"]
		pass

	def clean(self):
		cleaned = super().clean()
		s = cleaned.get("start_date")
		e = cleaned.get("end_date")
		if s and e and e < s:
			self.add_error("end_date", "End date must be on or after the start date.")
			pass
		return cleaned
		pass


class TermDatesForm(forms.ModelForm):

	class Meta:
		model  = TermConfig
		fields = ["start_date", "end_date"]
		widgets = {
			"start_date": forms.DateInput(attrs={"type": "date", "class": _DATE_CLASS}, format="%Y-%m-%d"),
			"end_date":   forms.DateInput(attrs={"type": "date", "class": _DATE_CLASS}, format="%Y-%m-%d"),
		}
		pass

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.fields["start_date"].input_formats = ["%Y-%m-%d"]
		self.fields["end_date"].input_formats   = ["%Y-%m-%d"]
		pass

	def clean(self):
		cleaned = super().clean()
		s = cleaned.get("start_date")
		e = cleaned.get("end_date")
		if s and e and e < s:
			self.add_error("end_date", "End date must be on or after the start date.")
			pass
		return cleaned
		pass


TermDatesFormSet = modelformset_factory(TermConfig, form=TermDatesForm, extra=0)


@login_required
def calendar_settings(request):
	school = request.school
	years  = AcademicYear.objects.filter(school=school).order_by("-start_date", "-name")

	year_id = request.GET.get("year") or request.POST.get("year")
	ay = None
	if year_id:
		ay = years.filter(pk=year_id).first()
		pass
	if ay is None:
		ay = get_active_academic_year(school)
		pass

	if ay is None:
		messages.error(request, "No academic year found. Create one first.")
		return redirect("scheduling:year_list")
		pass

	term_qs = TermConfig.objects.filter(academic_year=ay).order_by("term_number")

	if request.method == "POST":
		form    = AcademicYearDatesForm(request.POST, instance=ay)
		formset = TermDatesFormSet(request.POST, queryset=term_qs)
		if form.is_valid() and formset.is_valid():
			form.save()
			formset.save()
			messages.success(request, f"Calendar dates updated for {ay.name}.")
			return redirect(f"{reverse('scheduling:calendar_settings')}?year={ay.pk}")
			pass
	else:
		form    = AcademicYearDatesForm(instance=ay)
		formset = TermDatesFormSet(queryset=term_qs)
		pass

	return render(request, "scheduling/calendar_settings.html", {
		"form":          form,
		"formset":       formset,
		"academic_year": ay,
		"years":         years,
	})
	pass