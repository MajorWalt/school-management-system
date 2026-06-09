import datetime
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from core.decorators import tenant_required
from core.activity import log_activity
from accounts.models import UserRole
from scheduling.models import Homeroom
from students.models import Student
from .forms import AttendanceDateForm
from .models import Attendance
from .utils import is_school_day


def can_do_attendance(user, school):
	"""Admin or homeroom teacher."""
	if user.is_superuser:
		return True
	roles = UserRole.objects.filter(user=user, school=school).values_list("role", flat=True)
	if "admin" in roles:
		return True
	if "teacher" in roles:
		# Check if this teacher is assigned as a homeroom teacher
		try:
			staff = user.staff_profile
			return Homeroom.objects.filter(
				school=school,
				staff_members=staff
			).exists()
		except Exception:
			return False
	return False


def get_accessible_homerooms(user, school):
	"""Returns homerooms this user can mark attendance for."""
	if user.is_superuser:
		return Homeroom.objects.filter(school=school).select_related("form")
	roles = list(UserRole.objects.filter(user=user, school=school).values_list("role", flat=True))
	if "admin" in roles:
		return Homeroom.objects.filter(school=school).select_related("form")
	# Teacher — only their assigned homerooms
	try:
		staff = user.staff_profile
		return Homeroom.objects.filter(
			school=school,
			staff_members=staff
		).select_related("form")
	except Exception:
		return Homeroom.objects.none()


@login_required
@tenant_required
def attendance_home(request):
	"""Step 1 — pick a date."""
	if not can_do_attendance(request.user, request.school):
		messages.error(request, "Access denied.")
		return redirect("portals:dashboard")

	form = AttendanceDateForm(request.POST or None)

	if request.method == "POST" and form.is_valid():
		date = form.cleaned_data["date"]

		if not is_school_day(request.school, date):
			messages.warning(request, f"{date} is a non-school day. Attendance cannot be marked.")
		else:
			return redirect("attendance:homeroom_select", date=date.isoformat())

	# Show recent attendance summary
	today     = datetime.date.today()
	homerooms = get_accessible_homerooms(request.user, request.school)

	recent = []
	for hr in homerooms:
		students_count   = hr.students.filter(school=request.school).count()
		absences_today   = Attendance.objects.filter(
			school=request.school, homeroom=hr,
			date=today, status="absent"
		).count()
		last_marked = Attendance.objects.filter(
			school=request.school, homeroom=hr
		).order_by("-date").values_list("date", flat=True).first()

		recent.append({
			"homeroom":      hr,
			"students":      students_count,
			"absences_today": absences_today,
			"last_marked":   last_marked,
		})

	return render(request, "attendance/home.html", {
		"form":   form,
		"today":  today,
		"recent": recent,
	})


@login_required
@tenant_required
def homeroom_select(request, date):
	"""Step 2 — pick a homeroom."""
	if not can_do_attendance(request.user, request.school):
		messages.error(request, "Access denied.")
		return redirect("portals:dashboard")

	try:
		mark_date = datetime.date.fromisoformat(date)
	except ValueError:
		messages.error(request, "Invalid date.")
		return redirect("attendance:home")

	if not is_school_day(request.school, mark_date):
		messages.warning(request, f"{mark_date} is a non-school day.")
		return redirect("attendance:home")

	homerooms = get_accessible_homerooms(request.user, request.school)

	# If teacher only has one homeroom, skip straight to marking
	if homerooms.count() == 1:
		return redirect("attendance:mark", date=date, homeroom_pk=homerooms.first().pk)

	# Annotate with whether attendance has been marked already
	homeroom_status = []
	for hr in homerooms:
		marked = Attendance.objects.filter(
			school=request.school, homeroom=hr, date=mark_date
		).exists()
		homeroom_status.append({"homeroom": hr, "marked": marked})

	return render(request, "attendance/homeroom_select.html", {
		"homeroom_status": homeroom_status,
		"date":            mark_date,
	})


@login_required
@tenant_required
def attendance_mark(request, date, homeroom_pk):
	"""Step 3 — mark exceptions for the homeroom."""
	if not can_do_attendance(request.user, request.school):
		messages.error(request, "Access denied.")
		return redirect("portals:dashboard")

	homeroom = get_object_or_404(Homeroom, pk=homeroom_pk, school=request.school)

	try:
		mark_date = datetime.date.fromisoformat(date)
	except ValueError:
		messages.error(request, "Invalid date.")
		return redirect("attendance:home")

	if not is_school_day(request.school, mark_date):
		messages.warning(request, f"{mark_date} is a non-school day.")
		return redirect("attendance:home")

	# Only enrolled students in this homeroom
	students = Student.objects.filter(
		school=request.school,
		homeroom=homeroom,
	).order_by("last_name", "first_name")

	# Filter to currently enrolled only
	students = [s for s in students if s.current_status() == "enrolled"]

	# Pre-fetch existing exception records for this date
	existing = {
		a.student_id: a
		for a in Attendance.objects.filter(
			school=request.school,
			homeroom=homeroom,
			date=mark_date,
		)
	}

	if request.method == "POST":
		# Save only exceptions — delete present records if they exist
		saved = 0
		for student in students:
			status = request.POST.get(f"status_{student.pk}", "present")
			note   = request.POST.get(f"note_{student.pk}", "").strip()
			record = existing.get(student.pk)

			if status == "present":
				# Remove any existing exception record
				if record:
					record.delete()
			else:
				# Save exception
				if record:
					record.status    = status
					record.note      = note
					record.marked_by = request.user
					record.save()
				else:
					Attendance.objects.create(
						school    = request.school,
						student   = student,
						homeroom  = homeroom,
						date      = mark_date,
						status    = status,
						note      = note,
						marked_by = request.user,
					)
				saved += 1

		# Mark as "register submitted" — create a sentinel if zero exceptions
		# so we know attendance was taken even if everyone was present
		if saved == 0:
			Attendance.objects.get_or_create(
				school   = request.school,
				homeroom = homeroom,
				date     = mark_date,
				student  = students[0] if students else None,
				defaults = {
					"status":    "present",
					"marked_by": request.user,
				}
			)

		log_activity(request, "attendance_marked", f"Marked attendance for {homeroom} on {mark_date}.")
		messages.success(request, f"Attendance saved for {homeroom} on {mark_date}.")
		return redirect("attendance:home")

	# Build rows — default everyone to present
	rows = []
	for student in students:
		record = existing.get(student.pk)
		rows.append({
			"student": student,
			"status":  record.status if record else "present",
			"note":    record.note   if record else "",
		})

	return render(request, "attendance/mark.html", {
		"homeroom":  homeroom,
		"date":      mark_date,
		"rows":      rows,
		"statuses":  Attendance.STATUS_CHOICES,
		"exception_count": len([r for r in rows if r["status"] != "present"]),
	})


@login_required
@tenant_required
def attendance_report(request, homeroom_pk):
	"""Attendance history for a homeroom."""
	if not can_do_attendance(request.user, request.school):
		messages.error(request, "Access denied.")
		return redirect("portals:dashboard")

	homeroom = get_object_or_404(Homeroom, pk=homeroom_pk, school=request.school)

	# Get date range filter
	from_date = request.GET.get("from")
	to_date   = request.GET.get("to")

	records = Attendance.objects.filter(
		school=request.school,
		homeroom=homeroom,
	).exclude(status="present").select_related("student").order_by("-date", "student__last_name")

	if from_date:
		try:
			records = records.filter(date__gte=datetime.date.fromisoformat(from_date))
		except ValueError:
			pass
	if to_date:
		try:
			records = records.filter(date__lte=datetime.date.fromisoformat(to_date))
		except ValueError:
			pass

	# Group by date
	from itertools import groupby
	grouped = []
	for date, group in groupby(records, key=lambda r: r.date):
		grouped.append((date, list(group)))

	# Per-student summary
	students = Student.objects.filter(school=request.school, homeroom=homeroom)
	student_summary = []
	for student in students:
		absences = Attendance.objects.filter(
			school=request.school, homeroom=homeroom,
			student=student, status="absent"
		).count()
		lates = Attendance.objects.filter(
			school=request.school, homeroom=homeroom,
			student=student, status="late"
		).count()
		excused = Attendance.objects.filter(
			school=request.school, homeroom=homeroom,
			student=student, status="excused"
		).count()
		if absences or lates or excused:
			student_summary.append({
				"student":  student,
				"absences": absences,
				"lates":    lates,
				"excused":  excused,
			})

	student_summary.sort(key=lambda x: -x["absences"])

	return render(request, "attendance/report.html", {
		"homeroom":        homeroom,
		"grouped":         grouped,
		"student_summary": student_summary,
		"from_date":       from_date,
		"to_date":         to_date,
	})