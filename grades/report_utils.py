import calendar as pycal
import datetime
from django.db.models import Sum

from .models import Evaluation, GradeEntry
from .utils import compute_student_average


def _fmt(v):
	if v is None:
		return ""
		pass
	return f"{v:.1f}"
	pass


def _mean(values):
	vals = [v for v in values if v is not None]
	if not vals:
		return None
		pass
	return round(sum(vals) / len(vals), 1)
	pass


def _section_grades(school, student, section):
	"""(term_value, exam_value) for one section — coursework avg and final-exam mark."""
	evals = list(Evaluation.objects.filter(school=school, section=section))
	if not evals:
		return None, None
		pass

	entries = GradeEntry.objects.filter(school=school, student=student, evaluation__in=evals)
	gmap = {(e.evaluation_id, e.student_id): e for e in entries}

	course_evals = [e for e in evals if not e.is_final_exam]
	exam_evals   = [e for e in evals if e.is_final_exam]

	term_val = compute_student_average(student, course_evals, gmap)
	exam_val = compute_student_average(student, exam_evals, gmap)

	term_val = float(term_val) if term_val is not None else None
	exam_val = float(exam_val) if exam_val is not None else None
	return term_val, exam_val
	pass


def build_report_card(school, student, academic_year, up_to_term):
	"""
	Full per-subject x term grade matrix for one student, terms 1..up_to_term.
	All values are pre-formatted to strings so the xhtml2pdf template needs no filters.
	"""
	from scheduling.models import Enrolment, TermConfig

	terms = list(
		TermConfig.objects.filter(
			academic_year=academic_year, term_number__lte=up_to_term
		).order_by("term_number")
	)

	enrolments = list(
		Enrolment.objects.filter(
			student=student,
			section__academic_year=academic_year,
			section__term_number__lte=up_to_term,
		).select_related("section", "section__course", "section__teacher")
	)

	# Fall back to terms present in enrolments if TermConfig rows are missing.
	if not terms:
		present = sorted({e.section.term_number for e in enrolments})
		terms = [
			type("T", (), {"term_number": tn, "has_final_exam": False, "name": f"Term {tn}"})()
			for tn in present
		]
		pass

	exam_terms = {t.term_number for t in terms if getattr(t, "has_final_exam", False)}

	# Column layout: Term N, then Exam N only for terms with a final exam.
	columns = []
	for t in terms:
		columns.append({"label": f"Term {t.term_number}", "kind": "term", "term": t.term_number})
		if t.term_number in exam_terms:
			columns.append({"label": f"Exam {t.term_number}", "kind": "exam", "term": t.term_number})
			pass
		pass

	# Group sections by course.
	by_course = {}
	teachers = []
	for enr in enrolments:
		sec = enr.section
		rec = by_course.setdefault(sec.course.id, {"course": sec.course, "sections": {}})
		rec["sections"][sec.term_number] = sec
		if sec.teacher and sec.teacher not in teachers:
			teachers.append(sec.teacher)
			pass
		pass

	rows = []
	raw_rows = []  # keep numeric for column means
	for rec in sorted(by_course.values(), key=lambda r: r["course"].name.lower()):
		cells = []
		teacher_for_course = None
		for col in columns:
			sec = rec["sections"].get(col["term"])
			val = None
			if sec is not None:
				if teacher_for_course is None and sec.teacher:
					teacher_for_course = sec.teacher
					pass
				tval, eval_ = _section_grades(school, student, sec)
				val = tval if col["kind"] == "term" else eval_
				pass
			cells.append(val)
			pass

		avg = _mean(cells)
		raw_rows.append(cells)
		rows.append({
			"course":        rec["course"],
			"teacher":       teacher_for_course,
			"cells_display": [_fmt(v) for v in cells],
			"avg":           avg,
			"avg_display":   _fmt(avg),
		})
		pass

	col_averages = []
	for i in range(len(columns)):
		col_averages.append(_mean([cells[i] for cells in raw_rows]))
		pass

	overall = _mean([r["avg"] for r in rows])

	return {
		"columns":             columns,
		"rows":                rows,
		"col_averages_display": [_fmt(v) for v in col_averages],
		"overall":             overall,
		"overall_display":     _fmt(overall),
		"teachers":            teachers,
		"terms":               terms,
	}
	pass


def attendance_by_month(school, student, academic_year, as_of=None):
	from attendance.models import Attendance
	from attendance.utils import count_school_days

	start = getattr(academic_year, "start_date", None)
	end   = getattr(academic_year, "end_date", None)
	if not start or not end:
		return []
		pass

	if as_of is None:
		as_of = datetime.date.today()
		pass
	if end > as_of:
		end = as_of
		pass

	months = []
	y, m = start.year, start.month
	while (y < end.year) or (y == end.year and m <= end.month):
		m_start = datetime.date(y, m, 1)
		m_end   = datetime.date(y, m, pycal.monthrange(y, m)[1])
		if m_start < start:
			m_start = start
			pass
		if m_end > end:
			m_end = end
			pass

		open_days = count_school_days(school, m_start, m_end)
		absent = Attendance.objects.filter(
			school=school, student=student, status="absent",
			date__gte=m_start, date__lte=m_end,
		).count()
		late = Attendance.objects.filter(
			school=school, student=student, status="late",
			date__gte=m_start, date__lte=m_end,
		).count()
		if absent > open_days:
			absent = open_days
			pass

		months.append({
			"label":   m_start.strftime("%b"),
			"open":    open_days,
			"present": open_days - absent,
			"absent":  absent,
			"late":    late,
		})

		if m == 12:
			y, m = y + 1, 1
		else:
			m += 1
			pass
		pass

	return months
	pass


def conduct_by_term(school, student, terms):
	from merits.models import MeritRecord, DemeritRecord

	out = []
	for t in terms:
		s = getattr(t, "start_date", None)
		e = getattr(t, "end_date", None)
		if s and e:
			merits = MeritRecord.objects.filter(
				school=school, student=student, date__gte=s, date__lte=e
			).aggregate(x=Sum("count"))["x"] or 0
			demerits = DemeritRecord.objects.filter(
				school=school, student=student, date__gte=s, date__lte=e
			).aggregate(x=Sum("count"))["x"] or 0
			mer, dem = str(merits), str(demerits)
		else:
			mer, dem = "", ""
			pass

		out.append({
			"term":        t.term_number,
			"merits":      mer,
			"demerits":    dem,
			"detentions":  "0",   # behaviour app not built yet
			"suspensions": "0",
		})
		pass

	return out
	pass


def honours_label(overall, rows):
	if overall is None:
		return ""
		pass
	graded = [r["avg"] for r in rows if r["avg"] is not None]
	passed_all = all(a >= 55 for a in graded) if graded else False
	if overall >= 85 and passed_all:
		return "1st Class Honours"
		pass
	if overall >= 75 and passed_all:
		return "2nd Class Honours"
		pass
	return ""
	pass