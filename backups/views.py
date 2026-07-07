import os
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.conf import settings
from core.decorators import tenant_required, admin_required
from core.activity import log_activity
from accounts.models import UserRole
from .models import BackupLog
from .utils import run_backup


def is_admin(user, school):
    return UserRole.objects.filter(user=user, school=school, role="admin").exists() or user.is_superuser


@admin_required
@tenant_required
def backup_list(request):
    if not is_admin(request.user, request.school):
        messages.error(request, "Access denied.")
        return redirect("portals:dashboard")

    logs = BackupLog.objects.filter(school=request.school)
    return render(request, "backups/backup_list.html", {"logs": logs})


@admin_required
@tenant_required
def backup_run(request):
    if not is_admin(request.user, request.school):
        messages.error(request, "Access denied.")
        return redirect("portals:dashboard")

    if request.method != "POST":
        return redirect("backups:list")

    filepath, filename, file_size, error = run_backup(request.school.slug)

    if error:
        BackupLog.objects.create(
            school=request.school,
            triggered_by=request.user,
            filename=filename,
            status="failed",
            error_message=error,
        )
        messages.error(request, f"Backup failed: {error}")
    else:
        BackupLog.objects.create(
            school=request.school,
            triggered_by=request.user,
            filename=filename,
            file_size_bytes=file_size,
            status="success",
        )
        log_activity(request, "backup_run", f"Ran database backup: {filename}.")
        messages.success(request, f"Backup created: {filename}")

    return redirect("backups:list")


@admin_required
@tenant_required
def backup_download(request, pk):
    if not is_admin(request.user, request.school):
        raise Http404

    log = get_object_or_404(BackupLog, pk=pk, school=request.school, status="success")
    filepath = os.path.join(settings.MEDIA_ROOT, "backups", log.filename)

    if not os.path.exists(filepath):
        messages.error(request, "Backup file not found on disk.")
        return redirect("backups:list")

    response = FileResponse(
        open(filepath, "rb"),
        as_attachment=True,
        filename=log.filename,
    )
    return response


@admin_required
@tenant_required
def backup_delete(request, pk):
    if not is_admin(request.user, request.school):
        raise Http404

    log = get_object_or_404(BackupLog, pk=pk, school=request.school)
    filepath = os.path.join(settings.MEDIA_ROOT, "backups", log.filename)

    if os.path.exists(filepath):
        os.remove(filepath)

    log.delete()
    messages.warning(request, f"Backup {log.filename} deleted.")
    return redirect("backups:list")
