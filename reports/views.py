from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render
from core.decorators import tenant_required
from accounts.models import UserRole
from students.models import Student
from staff.models import Staff
from scheduling.models import AcademicYear, Enrolment, Form, Homeroom, Section
from merits.models import MeritRecord, DemeritRecord
from grades.models import Evaluation, GradeEntry, GradeWindow
from grades.utils import compute_student_average
from attendance.models import Attendance
import datetime
import calendar


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
		messages.error(request, "Access denied.")
		return redirect("portals:dashboard")

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
		messages.error(request, "Access denied.")
		return redirect("reports:home")

	form_pk     = request.GET.get("form")
	homeroom_pk = request.GET.get("homeroom")
	status      = request.GET.get("status", "enrolled")

	forms     = Form.objects.filter(school=school)
	homerooms = Homeroom.objects.filter(school=school).select_related("form")
	students  = Student.objects.filter(school=school).select_related("form", "homeroom", "house")

	if form_pk:
		students = students.filter(form_id=form_pk)
	if homeroom_pk:
		students = students.filter(homeroom_id=homeroom_pk)
	if status != "all":
		students = [s for s in students if s.current_status() == status]

	selected_form     = forms.filter(pk=form_pk).first()         if form_pk     else None
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
		messages.error(request, "Access denied.")
		return redirect("reports:home")

	dept   = request.GET.get("dept", "")
	active = request.GET.get("active", "1")

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
		"staff":           staff,
		"departments":     departments,
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
		messages.error(request, "Access denied.")
		return redirect("reports:home")

	homeroom_pk = request.GET.get("homeroom")

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
			"students":       students,
			"homeroom":       selected_homeroom,
			"school":         school,
			"school_profile": request.school_profile,
			"empty_cols":     range(20),
		}, filename=f"classlist_{selected_homeroom.name}.pdf")

	return render(request, "reports/class_list.html", {
		"homerooms":         homerooms,
		"selected_homeroom": selected_homeroom,
		"students":          students,
		"homeroom_pk":       homeroom_pk,
		"is_admin":          admin,
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
		messages.error(request, "Access denied.")
		return redirect("reports:home")

	section_pk = request.GET.get("section")
	year_pk    = request.GET.get("year")
	view       = request.GET.get("view", "kanban")

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
			"empty_cols":     range(20),
		}, filename=f"courselist_{selected_section.course.code or selected_section.course.name}.pdf")

	return render(request, "reports/course_list.html", {
		"sections":          sections,
		"selected_section":  selected_section,
		"enrolments":        enrolments,
		"years":             years,
		"selected_year":     year_pk,
		"section_pk":        section_pk,
		"view":              view,
		"is_admin":          admin,
	})


# ── Attendance Summary ────────────────────────────────────────────────────────

@login_required
@tenant_required
def attendance_summary(request):
	school = request.school
	admin  = is_admin(request.user, school)
	staff  = get_staff_profile(request.user)
	roles  = get_roles(request.user, school)

	if not admin and "teacher" not in roles:
		messages.error(request, "Access denied.")
		return redirect("reports:home")

	today       = datetime.date.today()
	month       = int(request.GET.get("month", today.month))
	year        = int(request.GET.get("year",  today.year))
	homeroom_pk = request.GET.get("homeroom")
	form_pk     = request.GET.get("form")

	if admin:
		homerooms = Homeroom.objects.filter(school=school).select_related("form")
	else:
		homerooms = Homeroom.objects.filter(
			school=school, staff_members=staff
		).select_related("form")

	forms = Form.objects.filter(school=school)

	selected_homeroom = homerooms.filter(pk=homeroom_pk).first() if homeroom_pk else None
	selected_form     = forms.filter(pk=form_pk).first()         if form_pk     else None

	first_day  = datetime.date(year, month, 1)
	last_day   = datetime.date(year, month, calendar.monthrange(year, month)[1])
	month_name = first_day.strftime("%B %Y")

	from scheduling.models import NonSchoolDay
	non_school_days = set(
		NonSchoolDay.objects.filter(
			school=school, date__gte=first_day, date__lte=last_day
		).values_list("date", flat=True)
	)

	school_days = []
	d = first_day
	while d <= last_day:
		if d.weekday() < 5 and d not in non_school_days:
			school_days.append(d)
		d += datetime.timedelta(days=1)

	days_open = len(school_days)

	students_qs = Student.objects.filter(school=school).select_related(
		"form", "homeroom"
	).order_by("last_name", "first_name")

	if selected_homeroom:
		students_qs = students_qs.filter(homeroom=selected_homeroom)
	elif selected_form:
		students_qs = students_qs.filter(form=selected_form)
	else:
		students_qs = students_qs.none()

	students_qs = [s for s in students_qs if s.current_status() in ("enrolled", "withdrawn")]

	if students_qs:
		att_records = Attendance.objects.filter(
			school=school,
			student__in=students_qs,
			date__gte=first_day,
			date__lte=last_day,
		)
		att_map = {}
		for rec in att_records:
			att_map[(rec.student_id, rec.date)] = rec
	else:
		att_map = {}

	from collections import defaultdict
	homeroom_groups = defaultdict(list)

	for student in students_qs:
		absent_unexec  = 0
		absent_excused = 0
		absent_other   = 0
		late_unexec    = 0
		late_excused   = 0

		for day in school_days:
			rec = att_map.get((student.pk, day))
			if rec is None:
				continue
			if rec.status == "absent":
				note = (rec.note or "").lower()
				if "excuse" in note or "sick" in note or "medical" in note:
					absent_excused += 1
				elif note:
					absent_other += 1
				else:
					absent_unexec += 1
			elif rec.status == "late":
				note = (rec.note or "").lower()
				if "excuse" in note:
					late_excused += 1
				else:
					late_unexec += 1

		absent_total = absent_unexec + absent_excused + absent_other
		attended     = days_open - absent_total

		def pct(n, total):
			if total == 0:
				return 0.0
			return round(n / total * 100, 2)

		hr_key = student.homeroom.name if student.homeroom else "No Homeroom"
		homeroom_groups[hr_key].append({
			"student":         student,
			"grade_homeroom":  f"{student.form}/{student.homeroom}" if student.form and student.homeroom else "—",
			"enrolled":        days_open,
			"attended":        attended,
			"absent_unexec":   absent_unexec,
			"absent_excused":  absent_excused,
			"absent_other":    absent_other,
			"absent_total":    absent_total,
			"late_unexec":     late_unexec,
			"late_excused":    late_excused,
			"att_pct":         pct(attended,       days_open),
			"abs_pct":         pct(absent_total,   days_open),
			"abs_unexec_pct":  pct(absent_unexec,  days_open),
			"abs_excused_pct": pct(absent_excused, days_open),
			"abs_other_pct":   pct(absent_other,   days_open),
			"late_u_pct":      pct(late_unexec,    days_open),
			"late_e_pct":      pct(late_excused,   days_open),
		})

	all_rows = [row for rows in homeroom_groups.values() for row in rows]
	grand = {
		"enrolled":       sum(r["enrolled"]       for r in all_rows),
		"attended":       sum(r["attended"]        for r in all_rows),
		"absent_unexec":  sum(r["absent_unexec"]   for r in all_rows),
		"absent_excused": sum(r["absent_excused"]  for r in all_rows),
		"absent_other":   sum(r["absent_other"]    for r in all_rows),
		"absent_total":   sum(r["absent_total"]    for r in all_rows),
		"late_unexec":    sum(r["late_unexec"]     for r in all_rows),
		"late_excused":   sum(r["late_excused"]    for r in all_rows),
	}
	grand["att_pct"] = round(grand["attended"]     / grand["enrolled"] * 100, 2) if grand["enrolled"] else 0.0
	grand["abs_pct"] = round(grand["absent_total"] / grand["enrolled"] * 100, 2) if grand["enrolled"] else 0.0

	month_choices = [(i, datetime.date(2000, i, 1).strftime("%B")) for i in range(1, 13)]
	year_choices  = list(range(today.year - 2, today.year + 2))

	context = {
		"homeroom_groups":   dict(homeroom_groups),
		"grand":             grand,
		"days_open":         days_open,
		"month_name":        month_name,
		"month":             month,
		"year":              year,
		"month_choices":     month_choices,
		"year_choices":      year_choices,
		"homerooms":         homerooms,
		"forms":             forms,
		"selected_homeroom": selected_homeroom,
		"selected_form":     selected_form,
		"homeroom_pk":       homeroom_pk,
		"form_pk":           form_pk,
		"is_admin":          admin,
		"all_rows":          all_rows,
	}

	as_pdf = request.GET.get("pdf") == "1"
	if as_pdf and all_rows:
		return _render_pdf(
			request,
			"reports/pdf/attendance_summary.html",
			context,
			filename=f"attendance_{month_name.replace(' ', '_')}.pdf"
		)

	return render(request, "reports/attendance_summary.html", context)


# ── Merit / Demerit Report ────────────────────────────────────────────────────

@login_required
@tenant_required
def merit_demerit_report(request):
	school = request.school
	if not is_admin(request.user, school):
		messages.error(request, "Access denied.")
		return redirect("reports:home")

	today        = datetime.date.today()
	month        = int(request.GET.get("month", today.month))
	year         = int(request.GET.get("year",  today.year))
	report_type  = request.GET.get("type", "merit")
	threshold_on = request.GET.get("threshold") == "1"

	first_day  = datetime.date(year, month, 1)
	last_day   = datetime.date(year, month, calendar.monthrange(year, month)[1])
	month_name = first_day.strftime("%B %Y")

	MIN_MERITS   = 10
	MIN_DEMERITS = 5

	from django.db.models import Sum
	from collections import OrderedDict

	if report_type == "merit":
		records_qs = MeritRecord.objects.filter(
			school=school, date__gte=first_day, date__lte=last_day
		).select_related("student", "awarded_by")

		student_totals = {
			r["student_id"]: r["total"]
			for r in records_qs.values("student_id").annotate(total=Sum("count"))
		}
		student_records = {}
		for rec in records_qs.order_by("student__last_name", "date"):
			student_records.setdefault(rec.student_id, []).append(rec)

		threshold       = MIN_MERITS
		threshold_label = f"{MIN_MERITS}+ merits"

	else:
		records_qs = DemeritRecord.objects.filter(
			school=school, date__gte=first_day, date__lte=last_day
		).select_related("student", "awarded_by")

		student_totals = {
			r["student_id"]: r["total"]
			for r in records_qs.values("student_id").annotate(total=Sum("count"))
		}
		student_records = {}
		for rec in records_qs.order_by("student__last_name", "date"):
			student_records.setdefault(rec.student_id, []).append(rec)

		threshold       = MIN_DEMERITS
		threshold_label = f"{MIN_DEMERITS}+ demerits"

	# Students who have records this month
	students = Student.objects.filter(
		school=school, pk__in=student_totals.keys()
	).select_related("form", "homeroom").order_by(
		"homeroom__name", "last_name", "first_name"
	)

	groups = OrderedDict()

	for student in students:
		pts = student_totals.get(student.pk, 0)

		if threshold_on and pts < threshold:
			continue

		hr_name = student.homeroom.name if student.homeroom else "No Homeroom"
		key     = hr_name

		if key not in groups:
			groups[key] = []

		groups[key].append({
			"student":   student,
			"points":    pts,
			"records":   student_records.get(student.pk, []),
			"threshold": pts >= threshold,
		})

	grand_points   = sum(student_totals.values())
	grand_students = len(student_totals)

	month_choices = [(i, datetime.date(2000, i, 1).strftime("%B")) for i in range(1, 13)]
	year_choices  = list(range(today.year - 2, today.year + 2))

	context = {
		"groups":          groups,
		"month_name":      month_name,
		"month":           month,
		"year":            year,
		"report_type":     report_type,
		"threshold_on":    threshold_on,
		"threshold":       threshold,
		"threshold_label": threshold_label,
		"grand_points":    grand_points,
		"grand_students":  grand_students,
		"month_choices":   month_choices,
		"year_choices":    year_choices,
		"min_merits":      MIN_MERITS,
		"min_demerits":    MIN_DEMERITS,
		"is_admin":        True,
	}

	as_pdf = request.GET.get("pdf") == "1"
	if as_pdf and groups:
		return _render_pdf(
			request,
			"reports/pdf/merit_demerit.html",
			context,
			filename=f"{'merits' if report_type == 'merit' else 'demerits'}_{month_name.replace(' ', '_')}.pdf"
		)

	return render(request, "reports/merit_demerit.html", context)


# ── PDF helper ────────────────────────────────────────────────────────────────

def _render_pdf(request, template_name, context, filename="report.pdf"):
	from django.template.loader import render_to_string
	import io

	context["generated_at"] = datetime.datetime.now().strftime("%A, %B %d, %Y")

	html_string = render_to_string(template_name, context, request=request)

	# Try WeasyPrint first (Linux / production)
	try:
		import weasyprint
		pdf      = weasyprint.HTML(string=html_string).write_pdf()
		response = HttpResponse(pdf, content_type="application/pdf")
		response["Content-Disposition"] = f'attachment; filename="{filename}"'
		return response
	except Exception:
		pass

	# Fall back to xhtml2pdf (Windows / dev)
	try:
		from xhtml2pdf import pisa
		buf = io.BytesIO()
		pisa.CreatePDF(html_string, dest=buf)
		buf.seek(0)
		response = HttpResponse(buf.read(), content_type="application/pdf")
		response["Content-Disposition"] = f'attachment; filename="{filename}"'
		return response
	except ImportError:
		return HttpResponse(
			"No PDF library available. Run: pip install xhtml2pdf",
			status=500
		)
	except Exception as e:
		return HttpResponse(f"PDF generation error: {e}", status=500)
	
# ── Grade Reports Home ────────────────────────────────────────────────────────

@login_required
@tenant_required
def grade_reports_home(request):
	school = request.school
	admin  = is_admin(request.user, school)
	if not admin:
		messages.error(request, "Access denied.")
		return redirect("reports:home")
	return render(request, "reports/grades/home.html", {"is_admin": admin})


# ── Grade Report by Course ────────────────────────────────────────────────────

@login_required
@tenant_required
def grade_by_course(request):
	school = request.school
	admin  = is_admin(request.user, school)
	if not admin:
		messages.error(request, "Access denied.")
		return redirect("reports:home")

	years      = AcademicYear.objects.filter(school=school).order_by("-name")
	year_pk    = request.GET.get("year")
	term       = request.GET.get("term")
	section_pk = request.GET.get("section")

	sections = Section.objects.filter(school=school).select_related(
		"course", "form", "academic_year", "teacher"
	)
	if year_pk:
		sections = sections.filter(academic_year_id=year_pk)
	if term:
		sections = sections.filter(term_number=term)

	selected_section = None
	rows             = []
	evaluations      = []

	if section_pk:
		selected_section = Section.objects.filter(
			pk=section_pk, school=school
		).select_related("course", "form", "academic_year", "teacher").first()

		if selected_section:
			evaluations = Evaluation.objects.filter(
				school=school, section=selected_section
			).order_by("date", "created_at")

			enrolments = Enrolment.objects.filter(
				section=selected_section
			).select_related("student").order_by(
				"student__last_name", "student__first_name"
			)

			entries = GradeEntry.objects.filter(
				school=school, evaluation__section=selected_section
			).select_related("evaluation", "student")
			grade_map = {(e.evaluation_id, e.student_id): e for e in entries}

			for enrolment in enrolments:
				student = enrolment.student
				cells   = []
				for ev in evaluations:
					entry = grade_map.get((ev.pk, student.pk))
					cells.append({
						"ev":     ev,
						"entry":  entry,
						"pct":    entry.percentage if entry else None,
						"absent": entry.is_absent  if entry else False,
					})
				avg = compute_student_average(student, evaluations, grade_map)
				rows.append({
					"student": student,
					"cells":   cells,
					"avg":     avg,
				})

	context = {
		"years":            years,
		"sections":         sections,
		"selected_section": selected_section,
		"evaluations":      evaluations,
		"rows":             rows,
		"year_pk":          year_pk,
		"term":             term,
		"section_pk":       section_pk,
		"is_admin":         admin,
	}

	as_pdf = request.GET.get("pdf") == "1"
	if as_pdf and selected_section and rows:
		return _render_pdf(
			request,
			"reports/pdf/grade_by_course.html",
			context,
			filename=f"grades_{selected_section.course.code or selected_section.course.name}_term{selected_section.term_number}.pdf"
		)

	return render(request, "reports/grades/by_course.html", context)


# ── Grade Report by Student ───────────────────────────────────────────────────

@login_required
@tenant_required
def grade_by_student(request):
	school     = request.school
	admin      = is_admin(request.user, school)
	if not admin:
		messages.error(request, "Access denied.")
		return redirect("reports:home")

	years      = AcademicYear.objects.filter(school=school).order_by("-name")
	year_pk    = request.GET.get("year")
	term       = request.GET.get("term")
	student_pk = request.GET.get("student")
	forms      = Form.objects.filter(school=school)
	homerooms  = Homeroom.objects.filter(school=school)
	form_pk    = request.GET.get("form")
	homeroom_pk= request.GET.get("homeroom")

	students_qs = Student.objects.filter(school=school).select_related(
		"form", "homeroom"
	).order_by("last_name", "first_name")
	if form_pk:
		students_qs = students_qs.filter(form_id=form_pk)
	if homeroom_pk:
		students_qs = students_qs.filter(homeroom_id=homeroom_pk)

	selected_student = Student.objects.filter(
		pk=student_pk, school=school
	).select_related("form", "homeroom").first() if student_pk else None

	course_rows = []

	if selected_student and year_pk:
		enrolments = Enrolment.objects.filter(
			student=selected_student,
			section__school=school,
			section__academic_year_id=year_pk,
		).select_related("section__course", "section__academic_year", "section__teacher")

		if term:
			enrolments = enrolments.filter(section__term_number=term)

		for enrolment in enrolments:
			section     = enrolment.section
			evaluations = Evaluation.objects.filter(
				school=school, section=section
			).order_by("date", "created_at")

			entries  = GradeEntry.objects.filter(
				school=school,
				evaluation__section=section,
				student=selected_student
			).select_related("evaluation")
			grade_map = {(e.evaluation_id, e.student_id): e for e in entries}

			cells = []
			for ev in evaluations:
				entry = grade_map.get((ev.pk, selected_student.pk))
				cells.append({
					"ev":     ev,
					"entry":  entry,
					"pct":    entry.percentage if entry else None,
					"absent": entry.is_absent  if entry else False,
				})
			avg = compute_student_average(selected_student, evaluations, grade_map)
			course_rows.append({
				"section":     section,
				"evaluations": evaluations,
				"cells":       cells,
				"avg":         avg,
			})

	context = {
		"years":            years,
		"forms":            forms,
		"homerooms":        homerooms,
		"students_qs":      students_qs,
		"selected_student": selected_student,
		"course_rows":      course_rows,
		"year_pk":          year_pk,
		"term":             term,
		"student_pk":       student_pk,
		"form_pk":          form_pk,
		"homeroom_pk":      homeroom_pk,
		"is_admin":         admin,
	}

	as_pdf = request.GET.get("pdf") == "1"
	if as_pdf and selected_student and course_rows:
		return _render_pdf(
			request,
			"reports/pdf/grade_by_student.html",
			context,
			filename=f"grades_{selected_student.last_name}_{selected_student.first_name}.pdf"
		)

	return render(request, "reports/grades/by_student.html", context)


# ── Teacher Gradebook (admin view) ────────────────────────────────────────────

@login_required
@tenant_required
def teacher_gradebook(request):
	school = request.school
	admin  = is_admin(request.user, school)
	if not admin:
		messages.error(request, "Access denied.")
		return redirect("reports:home")

	years      = AcademicYear.objects.filter(school=school).order_by("-name")
	year_pk    = request.GET.get("year")
	term       = request.GET.get("term")
	section_pk = request.GET.get("section")

	# Group sections by teacher
	sections = Section.objects.filter(school=school).select_related(
		"course", "form", "academic_year", "teacher"
	).order_by("teacher__last_name", "course__name")

	if year_pk:
		sections = sections.filter(academic_year_id=year_pk)
	if term:
		sections = sections.filter(term_number=term)

	from collections import defaultdict
	teacher_sections = defaultdict(list)
	for sec in sections:
		tname = sec.teacher.get_full_name() if sec.teacher else "Unassigned"
		teacher_sections[tname].append(sec)

	selected_section = None
	rows             = []
	evaluations      = []

	if section_pk:
		selected_section = Section.objects.filter(
			pk=section_pk, school=school
		).select_related("course", "form", "academic_year", "teacher").first()

		if selected_section:
			evaluations = Evaluation.objects.filter(
				school=school, section=selected_section
			).order_by("date", "created_at")

			enrolments = Enrolment.objects.filter(
				section=selected_section
			).select_related("student").order_by(
				"student__last_name", "student__first_name"
			)

			entries   = GradeEntry.objects.filter(
				school=school, evaluation__section=selected_section
			).select_related("evaluation", "student")
			grade_map = {(e.evaluation_id, e.student_id): e for e in entries}

			for enrolment in enrolments:
				student = enrolment.student
				cells   = []
				for ev in evaluations:
					entry = grade_map.get((ev.pk, student.pk))
					cells.append({
						"ev":     ev,
						"entry":  entry,
						"pct":    entry.percentage if entry else None,
						"absent": entry.is_absent  if entry else False,
					})
				avg = compute_student_average(student, evaluations, grade_map)
				rows.append({
					"student": student,
					"cells":   cells,
					"avg":     avg,
				})

	context = {
		"years":            years,
		"teacher_sections": dict(teacher_sections),
		"selected_section": selected_section,
		"evaluations":      evaluations,
		"rows":             rows,
		"year_pk":          year_pk,
		"term":             term,
		"section_pk":       section_pk,
		"is_admin":         admin,
	}

	as_pdf = request.GET.get("pdf") == "1"
	if as_pdf and selected_section and rows:
		return _render_pdf(
			request,
			"reports/pdf/grade_by_course.html",
			context,
			filename=f"gradebook_{selected_section.teacher.last_name if selected_section.teacher else 'unassigned'}_{selected_section.course.code or selected_section.course.name}.pdf"
		)

	return render(request, "reports/grades/teacher_gradebook.html", context)


# ── Grade Overview (form/homeroom matrix) ─────────────────────────────────────
@login_required
@tenant_required
def grade_overview(request):
	school      = request.school
	admin       = is_admin(request.user, school)
	if not admin:
		messages.error(request, "Access denied.")
		return redirect("reports:home")

	years       = AcademicYear.objects.filter(school=school).order_by("-name")
	year_pk     = request.GET.get("year")
	term        = request.GET.get("term")
	form_pk     = request.GET.get("form")
	homeroom_pk = request.GET.get("homeroom")
	forms       = Form.objects.filter(school=school)
	homerooms   = Homeroom.objects.filter(school=school).select_related("form")

	selected_form     = forms.filter(pk=form_pk).first()         if form_pk     else None
	selected_homeroom = homerooms.filter(pk=homeroom_pk).first() if homeroom_pk else None
	selected_year     = AcademicYear.objects.filter(
		pk=year_pk, school=school
	).first() if year_pk else None

	matrix_rows = []
	courses     = []

	if selected_year and (selected_form or selected_homeroom):
		students_qs = Student.objects.filter(school=school).select_related(
			"form", "homeroom"
		).order_by("last_name", "first_name")

		if selected_homeroom:
			students_qs = students_qs.filter(homeroom=selected_homeroom)
		elif selected_form:
			students_qs = students_qs.filter(form=selected_form)

		students_list = [s for s in students_qs if s.current_status() == "enrolled"]

		section_filter = Section.objects.filter(
			school=school, academic_year=selected_year
		)
		if selected_homeroom:
			section_filter = section_filter.filter(form=selected_homeroom.form)
		elif selected_form:
			section_filter = section_filter.filter(form=selected_form)
		if term:
			section_filter = section_filter.filter(term_number=term)

		section_filter = section_filter.select_related("course").order_by(
			"course__sequence", "course__name"
		)

		# Unique courses in order
		seen = {}
		for sec in section_filter:
			cname = sec.course.name
			if cname not in seen:
				seen[cname] = sec.course
		courses = list(seen.keys())

		# Pre-fetch all evaluations and grade entries
		all_evals = Evaluation.objects.filter(
			school=school, section__in=section_filter
		).select_related("section__course")

		all_entries = GradeEntry.objects.filter(
			school=school,
			evaluation__section__in=section_filter,
			student__in=students_list,
		).select_related("evaluation", "student")

		from collections import defaultdict
		ev_by_section_course = defaultdict(list)
		for ev in all_evals:
			ev_by_section_course[(ev.section_id, ev.section.course.name)].append(ev)

		entries_map = {}
		for ent in all_entries:
			entries_map[(ent.evaluation_id, ent.student_id)] = ent

		for student in students_list:
			course_avgs = {}

			for sec in section_filter:
				cname = sec.course.name
				evs   = ev_by_section_course.get((sec.pk, cname), [])
				if not evs:
					if cname not in course_avgs:
						course_avgs[cname] = None
					continue

				gmap = {}
				for ev in evs:
					ent = entries_map.get((ev.pk, student.pk))
					if ent:
						gmap[(ev.pk, student.pk)] = ent

				avg = compute_student_average(student, evs, gmap)

				# If same course appears across multiple terms, average them
				if cname in course_avgs and course_avgs[cname] is not None and avg is not None:
					course_avgs[cname] = round(
						(course_avgs[cname] + avg) / 2, 1
					)
				else:
					course_avgs[cname] = avg

			valid_avgs = [v for v in course_avgs.values() if v is not None]
			overall    = round(sum(valid_avgs) / len(valid_avgs), 1) if valid_avgs else None

			# Pre-flatten for PDF (avoids needing get_item in plain HTML templates)
			course_avgs_list = [course_avgs.get(c) for c in courses]

			matrix_rows.append({
				"student":          student,
				"course_avgs":      course_avgs,
				"course_avgs_list": course_avgs_list,
				"overall":          overall,
			})

	context = {
		"years":             years,
		"forms":             forms,
		"homerooms":         homerooms,
		"selected_year":     selected_year,
		"selected_form":     selected_form,
		"selected_homeroom": selected_homeroom,
		"year_pk":           year_pk,
		"form_pk":           form_pk,
		"homeroom_pk":       homeroom_pk,
		"term":              term,
		"courses":           courses,
		"matrix_rows":       matrix_rows,
		"is_admin":          admin,
		"is_ytd":            not bool(term),
	}

	as_pdf = request.GET.get("pdf") == "1"
	if as_pdf and matrix_rows:
		return _render_pdf(
			request,
			"reports/pdf/grade_overview.html",
			context,
			filename=f"grade_overview_{'ytd' if not term else 'term' + term}.pdf"
		)

	return render(request, "reports/grades/overview.html", context)