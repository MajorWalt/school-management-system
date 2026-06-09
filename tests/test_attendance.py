"""
Tests for the attendance app views:
  - attendance_section_select  (GET)
  - attendance_date_select     (GET, POST valid school day, POST non-school day)
  - attendance_mark            (GET, POST)
  - attendance_report          (GET)
"""
import datetime

from django.test import TestCase, Client
from django.urls import reverse

from accounts.models import User, UserRole
from attendance.models import Attendance
from core.models import School
from scheduling.models import AcademicYear, Course, Enrolment, Form, NonSchoolDay, Section
from students.models import Student, StudentStatusLog


class AttendanceViewTests(TestCase):
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

        self.year = AcademicYear.objects.create(
            school=self.school, name="2024-2025", is_current=True
        )
        self.form = Form.objects.create(school=self.school, name="Form 1", order=1)
        self.course = Course.objects.create(
            school=self.school, name="Mathematics", code="MATH"
        )
        self.section = Section.objects.create(
            school=self.school,
            course=self.course,
            academic_year=self.year,
            term_number=1,
            form=self.form,
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
        self.enrolment = Enrolment.objects.create(
            student=self.student, section=self.section
        )
        self.today = datetime.date.today()

    # ── section select ─────────────────────────────────────────────────────

    def test_section_select_requires_login(self):
        client = Client(SERVER_NAME="127.0.0.1")
        response = client.get(reverse("attendance:section_select"))
        self.assertEqual(response.status_code, 302)

    def test_section_select_returns_200(self):
        response = self.client.get(reverse("attendance:section_select"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "attendance/section_select.html")

    # ── date select ────────────────────────────────────────────────────────

    def test_date_select_get_returns_200(self):
        response = self.client.get(
            reverse(
                "attendance:date_select", kwargs={"section_pk": self.section.pk}
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "attendance/date_select.html")

    def test_date_select_post_valid_date_redirects_to_mark(self):
        date_str = self.today.isoformat()
        response = self.client.post(
            reverse(
                "attendance:date_select", kwargs={"section_pk": self.section.pk}
            ),
            {"date": date_str},
        )
        self.assertRedirects(
            response,
            reverse(
                "attendance:mark",
                kwargs={"section_pk": self.section.pk, "date": date_str},
            ),
            fetch_redirect_response=False,
        )

    def test_date_select_post_non_school_day_redirects_back(self):
        """If the selected date is a non-school day, redirect back with warning."""
        NonSchoolDay.objects.create(
            school=self.school,
            date=self.today,
            label="Holiday",
            type="holiday",
            created_by=self.admin_user,
        )
        response = self.client.post(
            reverse(
                "attendance:date_select", kwargs={"section_pk": self.section.pk}
            ),
            {"date": self.today.isoformat()},
        )
        self.assertRedirects(
            response,
            reverse(
                "attendance:date_select", kwargs={"section_pk": self.section.pk}
            ),
            fetch_redirect_response=False,
        )

    # ── attendance mark ────────────────────────────────────────────────────

    def test_attendance_mark_get_returns_200(self):
        response = self.client.get(
            reverse(
                "attendance:mark",
                kwargs={
                    "section_pk": self.section.pk,
                    "date": self.today.isoformat(),
                },
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "attendance/mark.html")

    def test_attendance_mark_invalid_date_redirects(self):
        response = self.client.get(
            reverse(
                "attendance:mark",
                kwargs={"section_pk": self.section.pk, "date": "not-a-date"},
            )
        )
        self.assertRedirects(
            response,
            reverse(
                "attendance:date_select", kwargs={"section_pk": self.section.pk}
            ),
            fetch_redirect_response=False,
        )

    def test_attendance_mark_post_creates_attendance_records(self):
        response = self.client.post(
            reverse(
                "attendance:mark",
                kwargs={
                    "section_pk": self.section.pk,
                    "date": self.today.isoformat(),
                },
            ),
            {f"status_{self.student.pk}": "present"},
        )
        self.assertRedirects(
            response,
            reverse("attendance:section_select"),
            fetch_redirect_response=False,
        )
        self.assertTrue(
            Attendance.objects.filter(
                school=self.school,
                student=self.student,
                section=self.section,
                date=self.today,
                status="present",
            ).exists()
        )

    def test_attendance_mark_post_updates_existing_record(self):
        Attendance.objects.create(
            school=self.school,
            student=self.student,
            section=self.section,
            date=self.today,
            status="present",
            marked_by=self.admin_user,
        )
        self.client.post(
            reverse(
                "attendance:mark",
                kwargs={
                    "section_pk": self.section.pk,
                    "date": self.today.isoformat(),
                },
            ),
            {f"status_{self.student.pk}": "absent"},
        )
        record = Attendance.objects.get(
            school=self.school,
            student=self.student,
            section=self.section,
            date=self.today,
        )
        self.assertEqual(record.status, "absent")

    # ── attendance report ──────────────────────────────────────────────────

    def test_attendance_report_returns_200(self):
        response = self.client.get(
            reverse("attendance:report", kwargs={"section_pk": self.section.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "attendance/report.html")

    def test_attendance_report_shows_grouped_records(self):
        Attendance.objects.create(
            school=self.school,
            student=self.student,
            section=self.section,
            date=self.today,
            status="absent",
            marked_by=self.admin_user,
        )
        response = self.client.get(
            reverse("attendance:report", kwargs={"section_pk": self.section.pk})
        )
        self.assertIn("grouped", response.context)
        self.assertEqual(len(response.context["grouped"]), 1)
