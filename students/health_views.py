from django import forms
from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.activity import log_activity
from core.decorators import admin_required, tenant_required

from .models import Student, StudentHealthRecord

INPUT_CLASSES = "w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"


class StudentHealthRecordForm(forms.ModelForm):
    class Meta:
        model = StudentHealthRecord
        fields = ["category", "title", "severity", "details", "action_plan", "is_active"]
        widgets = {
            "details": forms.Textarea(attrs={"rows": 3}),
            "action_plan": forms.Textarea(attrs={"rows": 3}),
        }
        help_texts = {
            "title": "e.g. Peanut allergy, Asthma, Insulin",
            "action_plan": "Emergency steps, medication location, who to call.",
            "is_active": "Untick if this no longer applies.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name != "is_active":
                field.widget.attrs["class"] = INPUT_CLASSES
        self.fields["is_active"].widget.attrs["class"] = "h-4 w-4 rounded border-gray-300 text-blue-600"
        pass


@admin_required
@tenant_required
def health_add(request, student_pk):
    student = get_object_or_404(Student, pk=student_pk, school=request.school)
    form = StudentHealthRecordForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            record = form.save(commit=False)
            record.school = request.school
            record.student = student
            record.recorded_by = request.user
            record.save()
            log_activity(request, "health_add", f"Added a {record.get_category_display().lower()} health record for {student.get_full_name()}.")
        messages.success(request, "Health record added.")
        return redirect("students:detail", pk=student.pk)
    return render(request, "students/health_form.html", {"form": form, "student": student, "record": None})
    pass


@admin_required
@tenant_required
def health_edit(request, pk):
    record = get_object_or_404(StudentHealthRecord.objects.select_related("student"), pk=pk, school=request.school)
    student = record.student
    form = StudentHealthRecordForm(request.POST or None, instance=record)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            form.save()
            log_activity(request, "health_edit", f"Edited a {record.get_category_display().lower()} health record for {student.get_full_name()}.")
        messages.success(request, "Health record updated.")
        return redirect("students:detail", pk=student.pk)
    return render(request, "students/health_form.html", {"form": form, "student": student, "record": record})
    pass


@admin_required
@tenant_required
@require_POST
def health_delete(request, pk):
    record = get_object_or_404(StudentHealthRecord.objects.select_related("student"), pk=pk, school=request.school)
    student = record.student
    with transaction.atomic():
        category = record.get_category_display().lower()
        record.delete()
        log_activity(request, "health_delete", f"Deleted a {category} health record for {student.get_full_name()}.")
    messages.success(request, "Health record deleted.")
    return redirect("students:detail", pk=student.pk)
    pass