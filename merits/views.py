from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.shortcuts import get_object_or_404, redirect, render
from core.decorators import tenant_required
from core.activity import log_activity
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
		log_activity(request, "merit_awarded", f"Awarded {record.count} merit(s) to {record.student.get_full_name()}.")
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
	student_name = record.student.get_full_name()
	record.delete()
	log_activity(request, "merit_deleted", f"Deleted merit record for {student_name}.")
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
		log_activity(request, "demerit_issued", f"Issued {record.count} demerit(s) to {record.student.get_full_name()}.")
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
	student_name = record.student.get_full_name()
	record.delete()
	log_activity(request, "demerit_deleted", f"Deleted demerit record for {student_name}.")
	messages.warning(request, "Demerit record deleted.")
	return redirect("merits:list")


@login_required
@tenant_required
def student_merit_report(request, student_pk):
	"""Per-student merit/demerit breakdown."""
	student  = get_object_or_404(Student, pk=student_pk, school=request.school)
	merits   = MeritRecord.objects.filter(school=request.school, student=student)
	demerits = DemeritRecord.objects.filter(school=request.school, student=student)

	merit_total   = merits.aggregate(total=Sum("count"))["total"] or 0
	demerit_total = demerits.aggregate(total=Sum("count"))["total"] or 0

	# Monthly breakdown
	merit_monthly = (
		merits.annotate(month=TruncMonth("date"))
		.values("month")
		.annotate(total=Sum("count"))
		.order_by("-month")
	)
	demerit_monthly = (
		demerits.annotate(month=TruncMonth("date"))
		.values("month")
		.annotate(total=Sum("count"))
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
	import datetime
	today = datetime.date.today()

	merit_monthly = (
		MeritRecord.objects.filter(school=request.school)
		.annotate(month=TruncMonth("date"))
		.values("month")
		.annotate(total=Sum("count"))
		.order_by("-month")
	)
	demerit_monthly = (
		DemeritRecord.objects.filter(school=request.school)
		.annotate(month=TruncMonth("date"))
		.values("month")
		.annotate(total=Sum("count"))
		.order_by("-month")
	)

	# Students with 10+ merits this month
	top_merits = (
		MeritRecord.objects.filter(
			school=request.school,
			date__year=today.year,
			date__month=today.month,
		)
		.values(
			"student__id",
			"student__first_name",
			"student__last_name",
			"student__homeroom__name",
			"student__form__name",
		)
		.annotate(total=Sum("count"))
		.filter(total__gte=10)
		.order_by("-total")
	)

	# Students with 5+ demerits this month
	top_demerits = (
		DemeritRecord.objects.filter(
			school=request.school,
			date__year=today.year,
			date__month=today.month,
		)
		.values(
			"student__id",
			"student__first_name",
			"student__last_name",
			"student__homeroom__name",
			"student__form__name",
		)
		.annotate(total=Sum("count"))
		.filter(total__gte=5)
		.order_by("-total")
	)

	return render(request, "merits/school_summary.html", {
		"merit_monthly":   merit_monthly,
		"today":           today,
		"demerit_monthly": demerit_monthly,
		"top_merits":      top_merits,
		"top_demerits":    top_demerits,
	})