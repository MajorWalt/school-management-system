from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.db.models import Sum
from core.decorators import tenant_required
from accounts.models import UserRole
from students.models import Student
from staff.models import Staff
from scheduling.models import AcademicYear, Section, Homeroom
from attendance.models import Attendance
from grades.models import ReportCard
from grades.utils import grades_visible_for_student
from merits.models import MeritRecord, DemeritRecord
import datetime


def get_roles(user, school):
	if not school:
		return []
	return list(
		UserRole.objects.filter(user=user, school=school).values_list("role", flat=True)
	)


@login_required
@tenant_required
def dashboard(request):
	roles = get_roles(request.user, request.school)

	if "admin" in roles:
		return redirect("portals:admin_dashboard")
	if "teacher" in roles:
		return redirect("portals:teacher_dashboard")
	if "student" in roles:
		return redirect("portals:student_dashboard")

	return render(request, "portals/no_role.html")


@login_required
@tenant_required
def admin_dashboard(request):
	roles = get_roles(request.user, request.school)
	if "admin" not in roles and not request.user.is_superuser:
		return redirect("portals:dashboard")

	today        = datetime.date.today()
	school       = request.school
	current_year = AcademicYear.objects.filter(school=school, is_current=True).first()

	stats = {
		"students": Student.objects.filter(school=school).count(),
		"staff":    Staff.objects.filter(school=school, active=True).count(),
		"sections": Section.objects.filter(school=school).count(),
		"absences_today": Attendance.objects.filter(
			school=school, date=today, status="absent"
		).count(),
		"report_cards": ReportCard.objects.filter(
			school=school, status="draft"
		).count(),
		"merits_this_month": MeritRecord.objects.filter(
			school=school,
			date__month=today.month,
			date__year=today.year,
		).aggregate(total=Sum("points"))["total"] or 0,
		"demerits_this_month": DemeritRecord.objects.filter(
			school=school,
			date__month=today.month,
			date__year=today.year,
		).aggregate(total=Sum("points"))["total"] or 0,
	}

	recent_absences = Attendance.objects.filter(
		school=school, status="absent"
	).select_related("student", "homeroom").order_by("-date")[:10]

	return render(request, "portals/admin_dashboard.html", {
		"stats":           stats,
		"current_year":    current_year,
		"recent_absences": recent_absences,
		"today":           today,
	})


@login_required
@tenant_required
def teacher_dashboard(request):
	roles = get_roles(request.user, request.school)
	if "teacher" not in roles and "admin" not in roles:
		return redirect("portals:dashboard")

	try:
		staff_profile = request.user.staff_profile
	except Staff.DoesNotExist:
		staff_profile = None

	today     = datetime.date.today()
	school    = request.school

	# Get homerooms this teacher is assigned to
	homerooms = Homeroom.objects.filter(
		school=school,
		staff_members=staff_profile,
	).select_related("form") if staff_profile else []

	homeroom_stats = []
	for hr in homerooms:
		total    = Student.objects.filter(school=school, homeroom=hr).count()
		absences = Attendance.objects.filter(
			school=school, homeroom=hr, date=today, status="absent"
		).count()
		lates = Attendance.objects.filter(
			school=school, homeroom=hr, date=today, status="late"
		).count()
		marked_today = Attendance.objects.filter(
			school=school, homeroom=hr, date=today
		).exists()
		homeroom_stats.append({
			"homeroom":     hr,
			"total":        total,
			"absences":     absences,
			"lates":        lates,
			"marked_today": marked_today,
		})

	# Sections this teacher teaches
	sections = Section.objects.filter(
		school=school,
		teacher=staff_profile,
	).select_related("course", "form", "academic_year") if staff_profile else []

	return render(request, "portals/teacher_dashboard.html", {
		"staff_profile":  staff_profile,
		"homeroom_stats": homeroom_stats,
		"sections":       sections,
		"today":          today,
	})


@login_required
@tenant_required
def student_dashboard(request):
	roles = get_roles(request.user, request.school)
	if "student" not in roles and "admin" not in roles:
		return redirect("portals:dashboard")

	try:
		student = request.user.student_profile
	except Student.DoesNotExist:
		return render(request, "portals/no_role.html")

	school       = request.school
	today        = datetime.date.today()
	can_see_grades = grades_visible_for_student(school, student)
	current_year = AcademicYear.objects.filter(school=school, is_current=True).first()

	# Attendance summary — count school days (any attendance record = school day)
	total_records  = Attendance.objects.filter(school=school, student=student).count()
	absent_records = Attendance.objects.filter(school=school, student=student, status="absent").count()
	attendance_pct = round(((total_records - absent_records) / total_records) * 100) if total_records else 100

	# Recent report cards
	report_cards = ReportCard.objects.filter(
		school=school, student=student, status="published"
	).select_related("academic_year").order_by("-academic_year__name", "term_number")

	# Merits / demerits
	merit_total = MeritRecord.objects.filter(
		school=school, student=student
	).aggregate(total=Sum("points"))["total"] or 0
	demerit_total = DemeritRecord.objects.filter(
		school=school, student=student
	).aggregate(total=Sum("points"))["total"] or 0

	# Recent attendance exceptions
	recent_attendance = Attendance.objects.filter(
		school=school, student=student
	).exclude(status="present").select_related("homeroom").order_by("-date")[:10]

	return render(request, "portals/student_dashboard.html", {
		"student":           student,
		"can_see_grades":    can_see_grades,
		"current_year":      current_year,
		"attendance_pct":    attendance_pct,
		"total_records":     total_records,
		"absent_records":    absent_records,
		"report_cards":      report_cards,
		"merit_total":       merit_total,
		"demerit_total":     demerit_total,
		"recent_attendance": recent_attendance,
		"today":             today,
	})