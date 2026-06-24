import datetime
import io

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string

from core.decorators import tenant_required
from scheduling.models import AcademicYear, TermConfig, Form, Homeroom
from students.models import Student
from .models import ReportCard
from .report_utils import (
	build_report_card, attendance_by_month, conduct_by_term, honours_label,
)


def _gather_students(school, form_id, homeroom_id, student_id):
	if student_id:
		return Student.objects.filter(school=school, pk=student_id)
		pass
	if homeroom_id:
		return (
			Student.objects.filter(school=school, homeroom_id=homeroom_id)
			.order_by("last_name", "first_name")
		)
		pass
	if form_id:
		return (
			Student.objects.filter(school=school, form_id=form_id)
			.order_by("homeroom__name", "last_name", "first_name")
		)
		pass
	return Student.objects.none()
	pass


@login_required
@tenant_required
def generate_report_cards(request):
	school       = request.school
	years        = AcademicYear.objects.filter(school=school).order_by("-is_current", "-name")
	active_year  = AcademicYear.objects.filter(school=school, is_current=True).first()
	forms        = Form.objects.filter(school=school).order_by("name")
	homerooms    = Homeroom.objects.filter(school=school).select_related("form").order_by("name")
	students     = Student.objects.filter(school=school).order_by("last_name", "first_name")

	if request.GET.get("generate"):
		year_id     = request.GET.get("year") or (active_year.pk if active_year else None)
		term        = request.GET.get("term")
		form_id     = request.GET.get("form") or None
		homeroom_id = request.GET.get("homeroom") or None
		student_id  = request.GET.get("student") or None

		year = AcademicYear.objects.filter(school=school, pk=year_id).first()
		if year is None or not term:
			messages.error(request, "Select an academic year and a term.")
			return _render_form(request, years, active_year, forms, homerooms, students)
			pass

		up_to_term = int(term)
		picked = _gather_students(school, form_id, homeroom_id, student_id)
		if not picked.exists():
			messages.error(request, "No students matched that selection.")
			return _render_form(request, years, active_year, forms, homerooms, students)
			pass

		terms = list(
			TermConfig.objects.filter(
				academic_year=year, term_number__lte=up_to_term
			).order_by("term_number")
		)

		cards = []
		for student in picked:
			data = build_report_card(school, student, year, up_to_term)
			data["student"]     = student
			data["attendance"]  = attendance_by_month(school, student, year)
			data["conduct"]     = conduct_by_term(school, student, terms or data["terms"])
			data["honours"]     = honours_label(data["overall"], data["rows"])

			rc = ReportCard.objects.filter(
				student=student, academic_year=year, term_number=up_to_term
			).first()
			data["comment"] = rc.comment if rc and rc.comment else ""
			cards.append(data)
			pass

		html = render_to_string("grades/report_card_pdf.html", {
			"cards":         cards,
			"school":        school,
			"academic_year": year,
			"term_number":   up_to_term,
			"today":         datetime.date.today(),
		})

		from xhtml2pdf import pisa
		buf = io.BytesIO()
		pisa.CreatePDF(html, dest=buf, encoding="utf-8")
		buf.seek(0)

		resp = HttpResponse(buf.read(), content_type="application/pdf")
		resp["Content-Disposition"] = f'inline; filename="report_cards_term{up_to_term}.pdf"'
		return resp
		pass

	return _render_form(request, years, active_year, forms, homerooms, students)
	pass


def _render_form(request, years, active_year, forms, homerooms, students):
	return render(request, "grades/report_card_generate.html", {
		"years":       years,
		"active_year": active_year,
		"forms":       forms,
		"homerooms":   homerooms,
		"students":    students,
	})
	pass