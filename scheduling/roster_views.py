from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404

from .models import Section, Enrolment, Homeroom
from students.models import Student


def _active_students(school, homeroom):
	"""
	Students in a homeroom. If you want to exclude withdrawn students,
	add the status filter here once you confirm the field name.
	"""
	return Student.objects.filter(school=school, homeroom=homeroom)
	pass


@login_required
def section_roster(request, pk):
	school  = request.school
	section = get_object_or_404(
		Section.objects.select_related("course", "form", "academic_year", "teacher"),
		pk=pk, school=school,
	)

	if request.method == "POST":
		action = request.POST.get("action")

		# --- Assign one or more whole homerooms ---
		if action == "assign_homerooms":
			hr_ids = request.POST.getlist("homerooms")
			added  = 0
			for hr in Homeroom.objects.filter(school=school, pk__in=hr_ids):
				for st in _active_students(school, hr):
					obj, created = Enrolment.objects.get_or_create(
						section=section, student=st,
						defaults={
							"source":          "homeroom",
							"source_homeroom": hr,
						},
					)
					if created:
						added += 1
						pass
					pass
				pass
			messages.success(request, f"Added {added} student(s) from homeroom assignment.")
			return redirect("scheduling:section_roster", pk=section.pk)
			pass

		# --- Add hand-picked individual students ---
		if action == "add_students":
			st_ids = request.POST.getlist("students")
			added  = 0
			for st in Student.objects.filter(school=school, pk__in=st_ids):
				obj, created = Enrolment.objects.get_or_create(
					section=section, student=st,
					defaults={"source": "manual"},
				)
				if created:
					added += 1
					pass
				pass
			messages.success(request, f"Enrolled {added} student(s).")
			return redirect("scheduling:section_roster", pk=section.pk)
			pass

		# --- Remove a single student ---
		if action == "remove":
			Enrolment.objects.filter(
				section=section, pk=request.POST.get("enrolment")
			).delete()
			messages.success(request, "Student removed from section.")
			return redirect("scheduling:section_roster", pk=section.pk)
			pass

		# --- Remove everyone that came from one homeroom assignment ---
		if action == "remove_homeroom":
			Enrolment.objects.filter(
				section=section, source_homeroom_id=request.POST.get("homeroom")
			).delete()
			messages.success(request, "Homeroom group removed from section.")
			return redirect("scheduling:section_roster", pk=section.pk)
			pass

		return redirect("scheduling:section_roster", pk=section.pk)
		pass

	# --- GET: build the page ---
	enrolments = (
		Enrolment.objects
		.filter(section=section)
		.select_related("student", "student__homeroom", "source_homeroom")
		.order_by("student__last_name", "student__first_name")
	)

	homerooms = Homeroom.objects.filter(school=school).select_related("form").order_by("name")

	# Individual-add picker: ?hr=<id> shows that homeroom's not-yet-enrolled students.
	pick_hr_id    = request.GET.get("hr")
	pick_homeroom = None
	pick_students = []
	if pick_hr_id:
		pick_homeroom = homerooms.filter(pk=pick_hr_id).first()
		if pick_homeroom is not None:
			enrolled_ids  = enrolments.values_list("student_id", flat=True)
			pick_students = (
				_active_students(school, pick_homeroom)
				.exclude(pk__in=enrolled_ids)
				.order_by("last_name", "first_name")
			)
			pass
		pass

	return render(request, "scheduling/section_roster.html", {
		"section":       section,
		"enrolments":    enrolments,
		"homerooms":     homerooms,
		"pick_homeroom": pick_homeroom,
		"pick_students": pick_students,
	})
	pass