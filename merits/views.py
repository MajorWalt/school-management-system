from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.shortcuts import get_object_or_404, redirect, render
from core.decorators import tenant_required
from students.models import Student
from .forms import DemeritForm, MeritForm
from .models import DemeritRecord, MeritRecord


@login_required
@tenant_required
def merit_list(request):
	merits   = MeritRecord.objects.filter(school=request.school).select_related("student", "awarded_by")
	demerits = DemeritRecord.objects.filter(school=request.school).select_related("student", "awarded_by")
	query    = request.GET.get("q", "")

	if query:
		merits = merits.filter(
			student__first_name__icontains=query
		) | merits.filter(
			student__last_name__icontains=query
		)
		demerits = demerits.filter(
			student__first_name__icontains=query
		) | demerits.filter(
			student__last_name__icontains=query
		)

	return render(request, "merits/merit_list.html", {
		"merits":   merits,
		"demerits": demerits,
		"query":    query,
	})


@login_required
@tenant_required
def merit_add(request):
	form = MeritForm(request.POST or None, school=request.school)
	if request.method == "POST" and form.is_valid():
		record = form.save(commit=False)
		record.school = request.school
		record.save()
		messages.success(request, f"Merit awarded to {record.student.get_full_name()}.")
		return redirect("merits:list")
	return render(request, "merits/merit_form.html", {
		"form":  form,
		"title": "Award Merit",
		"type":  "merit",
	})


@login_required
@tenant_required
def merit_delete(request, pk):
	record = get_object_or_404(MeritRecord, pk=pk, school=request.school)
	record.delete()
	messages.warning(request, "Merit record deleted.")
	return redirect("merits:list")


@login_required
@tenant_required
def demerit_add(request):
	form = DemeritForm(request.POST or None, school=request.school)
	if request.method == "POST" and form.is_valid():
		record = form.save(commit=False)
		record.school = request.school
		record.save()
		messages.success(request, f"Demerit issued to {record.student.get_full_name()}.")
		return redirect("merits:list")
	return render(request, "merits/merit_form.html", {
		"form":  form,
		"title": "Issue Demerit",
		"type":  "demerit",
	})


@login_required
@tenant_required
def demerit_delete(request, pk):
	record = get_object_or_404(DemeritRecord, pk=pk, school=request.school)
	record.delete()
	messages.warning(request, "Demerit record deleted.")
	return redirect("merits:list")


@login_required
@tenant_required
def student_merit_report(request, student_pk):
	"""Per-student merit/demerit breakdown."""
	student  = get_object_or_404(Student, pk=student_pk, school=request.school)
	merits   = MeritRecord.objects.filter(school=request.school, student=student)
	demerits = DemeritRecord.objects.filter(school=request.school, student=student)

	merit_total   = merits.aggregate(total=Sum("points"))["total"] or 0
	demerit_total = demerits.aggregate(total=Sum("points"))["total"] or 0

	# Monthly breakdown
	merit_monthly = (
		merits.annotate(month=TruncMonth("date"))
		.values("month")
		.annotate(total=Sum("points"))
		.order_by("-month")
	)
	demerit_monthly = (
		demerits.annotate(month=TruncMonth("date"))
		.values("month")
		.annotate(total=Sum("points"))
		.order_by("-month")
	)

	return render(request, "merits/student_report.html", {
		"student":        student,
		"merits":         merits,
		"demerits":       demerits,
		"merit_total":    merit_total,
		"demerit_total":  demerit_total,
		"merit_monthly":  merit_monthly,
		"demerit_monthly": demerit_monthly,
	})


@login_required
@tenant_required
def school_summary(request):
	"""School-wide monthly merit/demerit summary."""
	merit_monthly = (
		MeritRecord.objects.filter(school=request.school)
		.annotate(month=TruncMonth("date"))
		.values("month")
		.annotate(total=Sum("points"))
		.order_by("-month")
	)
	demerit_monthly = (
		DemeritRecord.objects.filter(school=request.school)
		.annotate(month=TruncMonth("date"))
		.values("month")
		.annotate(total=Sum("points"))
		.order_by("-month")
	)

	# Top merit students
	top_merits = (
		MeritRecord.objects.filter(school=request.school)
		.values("student__id", "student__first_name", "student__last_name")
		.annotate(total=Sum("points"))
		.order_by("-total")[:10]
	)

	# Top demerit students
	top_demerits = (
		DemeritRecord.objects.filter(school=request.school)
		.values("student__id", "student__first_name", "student__last_name")
		.annotate(total=Sum("points"))
		.order_by("-total")[:10]
	)

	return render(request, "merits/school_summary.html", {
		"merit_monthly":   merit_monthly,
		"demerit_monthly": demerit_monthly,
		"top_merits":      top_merits,
		"top_demerits":    top_demerits,
	})