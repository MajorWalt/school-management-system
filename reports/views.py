from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from core.decorators import tenant_required
from accounts.models import UserRole
from students.models import Student
from staff.models import Staff
from scheduling.models import Form, Homeroom, Section, AcademicYear
from scheduling.models import Enrolment


def get_roles(user, school):
	return list(UserRole.objects.filter(
		user=user, school=school
	).values_list("role", flat=True))


def is_admin(user, school):
	return UserRole.objects.filter(
		user=user, school=school, role="admin"
	).exists() or user.is_superuser


def get_staff_profile(user):
	try:
		return user.staff_profile
	except Exception:
		return None


# ── Reports Home ──────────────────────────────────────────────────────────────

@login_required
@tenant_required
def reports_home(request):
	school = request.school
	admin  = is_admin(request.user, school)
	staff  = get_staff_profile(request.user)
	roles  = get_roles(request.user, school)

	if not admin and "teacher" not in roles:
		from django.contrib import messages
		messages.error(request, "Access denied.")
		from django.shortcuts import redirect
		return redirect("portals:dashboard")

	# For teacher: get their sections and homerooms
	teacher_sections  = []
	teacher_homerooms = []
	if staff and not admin:
		teacher_sections  = Section.objects.filter(
			school=school, teacher=staff
		).select_related("course", "form", "academic_year")
		teacher_homerooms = Homeroom.objects.filter(
			school=school, staff_members=staff
		).select_related("form")

	forms     = Form.objects.filter(school=school)
	homerooms = Homeroom.objects.filter(school=school).select_related("form")
	years     = AcademicYear.objects.filter(school=school).order_by("-name")

	return render(request, "reports/home.html", {
		"is_admin":          admin,
		"teacher_sections":  teacher_sections,
		"teacher_homerooms": teacher_homerooms,
		"forms":             forms,
		"homerooms":         homerooms,
		"years":             years,
		"staff":             staff,
	})


# ── Student Roster ────────────────────────────────────────────────────────────

@login_required
@tenant_required
def student_roster(request):
	school = request.school
	if not is_admin(request.user, school):
		from django.contrib import messages
		messages.error(request, "Access denied.")
		from django.shortcuts import redirect
		return redirect("reports:home")

	form_pk     = request.GET.get("form")
	homeroom_pk = request.GET.get("homeroom")
	status      = request.GET.get("status", "enrolled")

	forms     = Form.objects.filter(school=school)
	homerooms = Homeroom.objects.filter(school=school).select_related("form")

	students = Student.objects.filter(school=school).select_related("form", "homeroom", "house")

	if form_pk:
		students = students.filter(form_id=form_pk)
	if homeroom_pk:
		students = students.filter(homeroom_id=homeroom_pk)
	if status != "all":
		students = [s for s in students if s.current_status() == status]

	selected_form     = forms.filter(pk=form_pk).first() if form_pk else None
	selected_homeroom = homerooms.filter(pk=homeroom_pk).first() if homeroom_pk else None

	as_pdf = request.GET.get("pdf") == "1"
	if as_pdf:
		return _render_pdf(request, "reports/pdf/student_roster.html", {
			"students":          students,
			"school":            school,
			"school_profile":    request.school_profile,
			"selected_form":     selected_form,
			"selected_homeroom": selected_homeroom,
			"status":            status,
		}, filename="student_roster.pdf")

	return render(request, "reports/student_roster.html", {
		"students":          students,
		"forms":             forms,
		"homerooms":         homerooms,
		"selected_form":     selected_form,
		"selected_homeroom": selected_homeroom,
		"status":            status,
		"form_pk":           form_pk,
		"homeroom_pk":       homeroom_pk,
	})


# ── Staff List ────────────────────────────────────────────────────────────────

@login_required
@tenant_required
def staff_list_report(request):
	school = request.school
	if not is_admin(request.user, school):
		from django.contrib import messages
		messages.error(request, "Access denied.")
		from django.shortcuts import redirect
		return redirect("reports:home")

	dept    = request.GET.get("dept", "")
	active  = request.GET.get("active", "1")

	staff = Staff.objects.filter(school=school)
	if dept:
		staff = staff.filter(department__icontains=dept)
	if active == "1":
		staff = staff.filter(active=True)
	elif active == "0":
		staff = staff.filter(active=False)

	departments = Staff.objects.filter(school=school).values_list(
		"department", flat=True
	).distinct().exclude(department="").order_by("department")

	as_pdf = request.GET.get("pdf") == "1"
	if as_pdf:
		return _render_pdf(request, "reports/pdf/staff_list.html", {
			"staff":          staff,
			"school":         school,
			"school_profile": request.school_profile,
		}, filename="staff_list.pdf")

	return render(request, "reports/staff_list.html", {
		"staff":       staff,
		"departments": departments,
		"selected_dept":   dept,
		"selected_active": active,
	})


# ── Class List ────────────────────────────────────────────────────────────────

@login_required
@tenant_required
def class_list(request):
	school = request.school
	admin  = is_admin(request.user, school)
	staff  = get_staff_profile(request.user)
	roles  = get_roles(request.user, school)

	if not admin and "teacher" not in roles:
		from django.contrib import messages
		messages.error(request, "Access denied.")
		from django.shortcuts import redirect
		return redirect("reports:home")

	homeroom_pk = request.GET.get("homeroom")

	# Teachers only see their own homerooms
	if admin:
		homerooms = Homeroom.objects.filter(school=school).select_related("form")
	else:
		homerooms = Homeroom.objects.filter(
			school=school, staff_members=staff
		).select_related("form")

	selected_homeroom = None
	students          = []

	if homeroom_pk:
		selected_homeroom = homerooms.filter(pk=homeroom_pk).first()
		if selected_homeroom:
			students = Student.objects.filter(
				school=school, homeroom=selected_homeroom
			).select_related("form", "house").order_by("last_name", "first_name")
			students = [s for s in students if s.current_status() == "enrolled"]

	as_pdf = request.GET.get("pdf") == "1"
	if as_pdf and selected_homeroom:
		return _render_pdf(request, "reports/pdf/class_list.html", {
			"students":        students,
			"homeroom":        selected_homeroom,
			"school":          school,
			"school_profile":  request.school_profile,
		}, filename=f"class_list_{selected_homeroom.name}.pdf")

	return render(request, "reports/class_list.html", {
		"homerooms":        homerooms,
		"selected_homeroom": selected_homeroom,
		"students":         students,
		"homeroom_pk":      homeroom_pk,
		"is_admin":         admin,
	})


# ── Course List ───────────────────────────────────────────────────────────────

@login_required
@tenant_required
def course_list_report(request):
	school = request.school
	admin  = is_admin(request.user, school)
	staff  = get_staff_profile(request.user)
	roles  = get_roles(request.user, school)

	if not admin and "teacher" not in roles:
		from django.contrib import messages
		messages.error(request, "Access denied.")
		from django.shortcuts import redirect
		return redirect("reports:home")

	section_pk = request.GET.get("section")
	year_pk    = request.GET.get("year")
	view       = request.GET.get("view", "kanban")

	# Filter sections by role
	if admin:
		sections = Section.objects.filter(school=school).select_related(
			"course", "form", "academic_year", "teacher"
		)
	else:
		sections = Section.objects.filter(
			school=school, teacher=staff
		).select_related("course", "form", "academic_year")

	years = AcademicYear.objects.filter(school=school).order_by("-name")
	if year_pk:
		sections = sections.filter(academic_year_id=year_pk)

	selected_section = None
	enrolments       = []

	if section_pk:
		selected_section = sections.filter(pk=section_pk).first()
		if selected_section:
			enrolments = Enrolment.objects.filter(
				section=selected_section
			).select_related("student").order_by(
				"student__last_name", "student__first_name"
			)

	as_pdf = request.GET.get("pdf") == "1"
	if as_pdf and selected_section:
		return _render_pdf(request, "reports/pdf/course_list.html", {
			"section":        selected_section,
			"enrolments":     enrolments,
			"school":         school,
			"school_profile": request.school_profile,
		}, filename=f"course_list_{selected_section.course.code or selected_section.course.name}.pdf")

	return render(request, "reports/course_list.html", {
		"sections":         sections,
		"selected_section": selected_section,
		"enrolments":       enrolments,
		"years":            years,
		"selected_year":    year_pk,
		"section_pk":       section_pk,
		"view":             view,
		"is_admin":         admin,
	})


# ── PDF helper ────────────────────────────────────────────────────────────────

def _render_pdf(request, template_name, context, filename="report.pdf"):
	from django.template.loader import render_to_string
	import io
	import datetime

	# Inject generated_at so PDF templates don't need {% now %}
	context["generated_at"] = datetime.datetime.now().strftime("%d %b %Y %H:%M")

	html_string = render_to_string(template_name, context, request=request)

	# Try WeasyPrint first (Linux/production)
	try:
		import weasyprint
		pdf      = weasyprint.HTML(string=html_string).write_pdf()
		response = HttpResponse(pdf, content_type="application/pdf")
		response["Content-Disposition"] = f'attachment; filename="{filename}"'
		return response
	except Exception:
		pass

	# Fall back to xhtml2pdf (Windows/dev)
	try:
		from xhtml2pdf import pisa
		buf = io.BytesIO()
		pisa.CreatePDF(html_string, dest=buf)
		buf.seek(0)
		response = HttpResponse(buf.read(), content_type="application/pdf")
		response["Content-Disposition"] = f'attachment; filename="{filename}"'
		return response
	except ImportError:
		return HttpResponse("No PDF library available. Run: pip install xhtml2pdf", status=500)
	except Exception as e:
		return HttpResponse(f"PDF generation error: {e}", status=500)