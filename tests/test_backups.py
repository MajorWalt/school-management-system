"""
Tests for the backups app views:
  - backup_list     (GET — admin only)
  - backup_run      (POST — admin only, GET redirects to list)
  - backup_download (GET — admin only, file missing → redirect)
  - backup_delete   (GET — admin only)
"""
import os
import tempfile

from django.test import TestCase, Client, override_settings
from django.urls import reverse

from accounts.models import User, UserRole
from backups.models import BackupLog
from core.models import School


class BackupsViewTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name="Test School", slug="testschool", is_active=True
        )
        self.admin_user = User.objects.create_user(
            email="admin@test.com",
            password="password123",
            first_name="Admin",
            last_name="User",
        )
        UserRole.objects.create(user=self.admin_user, school=self.school, role="admin")
        self.client = Client(SERVER_NAME="127.0.0.1")
        self.client.login(username="admin@test.com", password="password123")

        self.non_admin_user = User.objects.create_user(
            email="teacher@test.com",
            password="password123",
            first_name="Teacher",
            last_name="User",
        )
        UserRole.objects.create(
            user=self.non_admin_user, school=self.school, role="teacher"
        )

    # ── backup_list ────────────────────────────────────────────────────────

    def test_backup_list_requires_login(self):
        client = Client(SERVER_NAME="127.0.0.1")
        response = client.get(reverse("backups:list"))
        self.assertEqual(response.status_code, 302)

    def test_backup_list_returns_200_for_admin(self):
        response = self.client.get(reverse("backups:list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "backups/backup_list.html")

    def test_backup_list_redirects_non_admin(self):
        self.client.login(username="teacher@test.com", password="password123")
        response = self.client.get(reverse("backups:list"))
        self.assertRedirects(
            response,
            reverse("portals:dashboard"),
            fetch_redirect_response=False,
        )

    # ── backup_run ─────────────────────────────────────────────────────────

    def test_backup_run_get_redirects_to_list(self):
        response = self.client.get(reverse("backups:run"))
        self.assertRedirects(
            response, reverse("backups:list"), fetch_redirect_response=False
        )

    def test_backup_run_post_non_admin_redirects(self):
        self.client.login(username="teacher@test.com", password="password123")
        response = self.client.post(reverse("backups:run"))
        self.assertRedirects(
            response,
            reverse("portals:dashboard"),
            fetch_redirect_response=False,
        )

    def test_backup_run_post_creates_backup_log(self):
        """
        run_backup() will either succeed or fail depending on the environment.
        Either way, a BackupLog record should be created.
        """
        initial_count = BackupLog.objects.filter(school=self.school).count()
        self.client.post(reverse("backups:run"))
        final_count = BackupLog.objects.filter(school=self.school).count()
        self.assertEqual(final_count, initial_count + 1)

    # ── backup_download ────────────────────────────────────────────────────

    def test_backup_download_404_for_non_admin(self):
        log = BackupLog.objects.create(
            school=self.school,
            triggered_by=self.admin_user,
            filename="backup.gz",
            status="success",
        )
        self.client.login(username="teacher@test.com", password="password123")
        response = self.client.get(
            reverse("backups:download", kwargs={"pk": log.pk})
        )
        self.assertEqual(response.status_code, 404)

    def test_backup_download_missing_file_redirects(self):
        """A backup log that exists but whose file is missing on disk redirects."""
        log = BackupLog.objects.create(
            school=self.school,
            triggered_by=self.admin_user,
            filename="nonexistent_backup.gz",
            status="success",
        )
        response = self.client.get(
            reverse("backups:download", kwargs={"pk": log.pk})
        )
        self.assertRedirects(
            response, reverse("backups:list"), fetch_redirect_response=False
        )

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_backup_download_streams_file(self):
        """When the backup file exists, it should stream with status 200."""
        import django.conf
        backup_dir = os.path.join(django.conf.settings.MEDIA_ROOT, "backups")
        os.makedirs(backup_dir, exist_ok=True)
        filename = "test_backup.gz"
        filepath = os.path.join(backup_dir, filename)
        with open(filepath, "wb") as f:
            f.write(b"fake gzip data")

        log = BackupLog.objects.create(
            school=self.school,
            triggered_by=self.admin_user,
            filename=filename,
            file_size_bytes=14,
            status="success",
        )
        response = self.client.get(
            reverse("backups:download", kwargs={"pk": log.pk})
        )
        self.assertEqual(response.status_code, 200)

    # ── backup_delete ──────────────────────────────────────────────────────

    def test_backup_delete_404_for_non_admin(self):
        log = BackupLog.objects.create(
            school=self.school,
            triggered_by=self.admin_user,
            filename="backup.gz",
            status="success",
        )
        self.client.login(username="teacher@test.com", password="password123")
        response = self.client.get(
            reverse("backups:delete", kwargs={"pk": log.pk})
        )
        self.assertEqual(response.status_code, 404)

    def test_backup_delete_removes_log(self):
        log = BackupLog.objects.create(
            school=self.school,
            triggered_by=self.admin_user,
            filename="backup_to_delete.gz",
            status="success",
        )
        response = self.client.get(
            reverse("backups:delete", kwargs={"pk": log.pk})
        )
        self.assertRedirects(
            response, reverse("backups:list"), fetch_redirect_response=False
        )
        self.assertFalse(BackupLog.objects.filter(pk=log.pk).exists())
