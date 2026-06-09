"""
Tests for the merits app views:
  - merit_list        (GET, search)
  - merit_add         (GET, POST)
  - merit_delete      (GET)
  - demerit_add       (GET, POST)
  - demerit_delete    (GET)
  - student_merit_report (GET)
  - school_summary    (GET)
"""
import datetime

from django.test import TestCase, Client
from django.urls import reverse

from accounts.models import User, UserRole
from core.models import School
from merits.models import DemeritRecord, MeritRecord
from staff.models import Staff
from students.models import Student, StudentStatusLog


class MeritsViewTests(TestCase):
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

        self.staff_member = Staff.objects.create(
            school=self.school,
            employee_number="EMP001",
            first_name="Jane",
            last_name="Smith",
        )
        self.student = Student.objects.create(
            school=self.school,
            student_id="S001",
            first_name="Alice",
            last_name="Jones",
        )
        StudentStatusLog.objects.create(
            student=self.student,
            status="enrolled",
            change_date=datetime.date.today(),
            changed_by=self.admin_user,
        )

    # ── merit_list ─────────────────────────────────────────────────────────

    def test_merit_list_returns_200(self):
        response = self.client.get(reverse("merits:list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "merits/merit_list.html")

    def test_merit_list_requires_login(self):
        client = Client(SERVER_NAME="127.0.0.1")
        response = client.get(reverse("merits:list"))
        self.assertEqual(response.status_code, 302)

    def test_merit_list_search(self):
        MeritRecord.objects.create(
            school=self.school,
            student=self.student,
            category="academic",
            reason="Top of class",
            points=5,
            date=datetime.date.today(),
        )
        response = self.client.get(reverse("merits:list") + "?q=Alice")
        self.assertEqual(response.status_code, 200)

    # ── merit_add ──────────────────────────────────────────────────────────

    def test_merit_add_get_returns_200(self):
        response = self.client.get(reverse("merits:add"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "merits/merit_form.html")

    def test_merit_add_post_creates_merit(self):
        response = self.client.post(
            reverse("merits:add"),
            {
                "student": self.student.pk,
                "awarded_by": self.staff_member.pk,
                "category": "academic",
                "reason": "Excellent performance",
                "points": 10,
                "date": datetime.date.today().isoformat(),
            },
        )
        self.assertRedirects(
            response, reverse("merits:list"), fetch_redirect_response=False
        )
        self.assertTrue(
            MeritRecord.objects.filter(
                school=self.school, student=self.student
            ).exists()
        )

    def test_merit_add_post_invalid_rerenders(self):
        response = self.client.post(
            reverse("merits:add"),
            {"student": "", "category": "", "reason": "", "points": ""},
        )
        self.assertEqual(response.status_code, 200)

    # ── merit_delete ───────────────────────────────────────────────────────

    def test_merit_delete(self):
        merit = MeritRecord.objects.create(
            school=self.school,
            student=self.student,
            category="academic",
            reason="Test",
            points=5,
            date=datetime.date.today(),
        )
        response = self.client.get(
            reverse("merits:delete", kwargs={"pk": merit.pk})
        )
        self.assertRedirects(
            response, reverse("merits:list"), fetch_redirect_response=False
        )
        self.assertFalse(MeritRecord.objects.filter(pk=merit.pk).exists())

    # ── demerit_add ────────────────────────────────────────────────────────

    def test_demerit_add_get_returns_200(self):
        response = self.client.get(reverse("merits:demerit_add"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "merits/merit_form.html")

    def test_demerit_add_post_creates_demerit(self):
        response = self.client.post(
            reverse("merits:demerit_add"),
            {
                "student": self.student.pk,
                "awarded_by": self.staff_member.pk,
                "category": "tardiness",
                "reason": "Late to class",
                "points": 3,
                "date": datetime.date.today().isoformat(),
            },
        )
        self.assertRedirects(
            response, reverse("merits:list"), fetch_redirect_response=False
        )
        self.assertTrue(
            DemeritRecord.objects.filter(
                school=self.school, student=self.student
            ).exists()
        )

    # ── demerit_delete ─────────────────────────────────────────────────────

    def test_demerit_delete(self):
        demerit = DemeritRecord.objects.create(
            school=self.school,
            student=self.student,
            category="behaviour",
            reason="Test",
            points=3,
            date=datetime.date.today(),
        )
        response = self.client.get(
            reverse("merits:demerit_delete", kwargs={"pk": demerit.pk})
        )
        self.assertRedirects(
            response, reverse("merits:list"), fetch_redirect_response=False
        )
        self.assertFalse(DemeritRecord.objects.filter(pk=demerit.pk).exists())

    # ── student_merit_report ───────────────────────────────────────────────

    def test_student_merit_report_returns_200(self):
        response = self.client.get(
            reverse("merits:student_report", kwargs={"student_pk": self.student.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "merits/student_report.html")

    def test_student_merit_report_context(self):
        MeritRecord.objects.create(
            school=self.school,
            student=self.student,
            category="academic",
            reason="Test",
            points=5,
            date=datetime.date.today(),
        )
        response = self.client.get(
            reverse("merits:student_report", kwargs={"student_pk": self.student.pk})
        )
        self.assertEqual(response.context["merit_total"], 5)
        self.assertEqual(response.context["demerit_total"], 0)

    # ── school_summary ─────────────────────────────────────────────────────

    def test_school_summary_returns_200(self):
        response = self.client.get(reverse("merits:summary"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "merits/school_summary.html")

    def test_school_summary_context_keys(self):
        response = self.client.get(reverse("merits:summary"))
        for key in ("merit_monthly", "demerit_monthly", "top_merits", "top_demerits"):
            self.assertIn(key, response.context)
