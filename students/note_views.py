from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, get_object_or_404

from core.decorators import tenant_required
from accounts.models import UserRole
from .models import Student, StudentNote


def _roles(user, school):
	if not school:
		return []
		pass
	return list(
		UserRole.objects.filter(user=user, school=school).values_list("role", flat=True)
	)
	pass


def _is_staff(user, school):
	roles = _roles(user, school)
	return user.is_superuser or "admin" in roles or "teacher" in roles
	pass


def _is_admin(user, school):
	return user.is_superuser or "admin" in _roles(user, school)
	pass


@login_required
@tenant_required
def note_add(request, student_pk):
	school  = request.school
	student = get_object_or_404(Student, pk=student_pk, school=school)

	if not _is_staff(request.user, school):
		messages.error(request, "You don't have permission to add notes.")
		return redirect("students:detail", pk=student.pk)
		pass

	if request.method == "POST":
		body = (request.POST.get("body") or "").strip()
		if body:
			StudentNote.objects.create(
				school=school, student=student, body=body, author=request.user
			)
			messages.success(request, "Note added.")
		else:
			messages.error(request, "Note can't be empty.")
			pass
		pass

	return redirect("students:detail", pk=student.pk)
	pass


@login_required
@tenant_required
def note_edit(request, pk):
	school = request.school
	note   = get_object_or_404(StudentNote, pk=pk, school=school)

	# Author can edit own; admin can edit any.
	if not (_is_admin(request.user, school) or note.author_id == request.user.id):
		messages.error(request, "You can only edit your own notes.")
		return redirect("students:detail", pk=note.student_id)
		pass

	if request.method == "POST":
		body = (request.POST.get("body") or "").strip()
		if body:
			note.body = body
			note.save(update_fields=["body", "updated_at"])
			messages.success(request, "Note updated.")
		else:
			messages.error(request, "Note can't be empty.")
			pass
		pass

	return redirect("students:detail", pk=note.student_id)
	pass


@login_required
@tenant_required
def note_delete(request, pk):
	school = request.school
	note   = get_object_or_404(StudentNote, pk=pk, school=school)

	# Admin only.
	if not _is_admin(request.user, school):
		messages.error(request, "Only admins can delete notes.")
		return redirect("students:detail", pk=note.student_id)
		pass

	if request.method == "POST":
		student_id = note.student_id
		note.delete()
		messages.success(request, "Note deleted.")
		return redirect("students:detail", pk=student_id)
		pass

	return redirect("students:detail", pk=note.student_id)
	pass