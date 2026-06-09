"""
Tests for the portals app views:
  - dashboard (role dispatcher)
  - admin_dashboard
  - teacher_dashboard
  - student_dashboard
"""
import datetime

from django.test import TestCase, Client
from django.urls import reverse

from accounts.models import User, UserRole
from attendance.models import Attendance
from core.models import School
from grades.models import GradeVisibilityRule, ReportCard
from merits.models import DemeritRecord, MeritRecord
from scheduling.models import AcademicYear, Course, Enrolment, Form, Section
from staff.models import Staff
from students.models import Student, StudentStatusLog


class PortalsDashboardTests(TestCase):
    """Tests for the dashboard role-dispatch view."""

    def setUp(self):
        self.school = School.objects.create(
            name="Test School", slug="testschool", is_active=True
        )
        self.client = Client(SERVER_NAME="127.0.0.1")

    def _login(self, user):
        self.client.login(username=user.email, password="password123")

    def _make_user(self, email, role):
        user = User.objects.create_user(
            email=email, password="password123", first_name="A", last_name="B"
        )
        UserRole.objects.create(user=user, school=self.school, role=role)
        return user

    def test_dashboard_redirects_admin_to_admin_dashboard(self):
        user = self._make_user("admin@t.com", "admin")
        self._login(user)
        response = self.client.get(reverse("portals:dashboard"))
        self.assertRedirects(
            response, reverse("portals:admin_dashboard"), fetch_redirect_response=False
        )

    def test_dashboard_redirects_teacher_to_teacher_dashboard(self):
        user = self._make_user("teacher@t.com", "teacher")
        self._login(user)
        response = self.client.get(reverse("portals:dashboard"))
        self.assertRedirects(
            response,
            reverse("portals:teacher_dashboard"),
            fetch_redirect_response=False,
        )

    def test_dashboard_redirects_student_to_student_dashboard(self):
        user = self._make_user("student@t.com", "student")
        self._login(user)
        response = self.client.get(reverse("portals:dashboard"))
        self.assertRedirects(
            response,
            reverse("portals:student_dashboard"),
            fetch_redirect_response=False,
        )

    def test_dashboard_no_role_renders_no_role_template(self):
        user = User.objects.create_user(
            email="norole@t.com", password="password123", first_name="X", last_name="Y"
        )
        self._login(user)
        response = self.client.get(reverse("portals:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "portals/no_role.html")

    def test_dashboard_unauthenticated_redirects_to_login(self):
        response = self.client.get(reverse("portals:dashboard"))
        self.assertRedirects(
            response,
            "/accounts/login/?next=/",
            fetch_redirect_response=False,
        )


class AdminDashboardTests(TestCase):
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
        UserRole.objects.create(
            user=self.admin_user, school=self.school, role="admin"
        )
        self.client = Client(SERVER_NAME="127.0.0.1")
        self.client.login(username="admin@test.com", password="password123")

    def test_admin_dashboard_returns_200_for_admin(self):
        response = self.client.get(reverse("portals:admin_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "portals/admin_dashboard.html")

    def test_admin_dashboard_contains_stats(self):
        response = self.client.get(reverse("portals:admin_dashboard"))
        self.assertIn("stats", response.context)

    def test_non_admin_redirected_from_admin_dashboard(self):
        teacher = User.objects.create_user(
            email="teacher@test.com",
            password="password123",
            first_name="T",
            last_name="U",
        )
        UserRole.objects.create(user=teacher, school=self.school, role="teacher")
        self.client.login(username="teacher@test.com", password="password123")
        response = self.client.get(reverse("portals:admin_dashboard"))
        self.assertRedirects(
            response, reverse("portals:dashboard"), fetch_redirect_response=False
        )


class TeacherDashboardTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name="Test School", slug="testschool", is_active=True
        )
        self.teacher_user = User.objects.create_user(
            email="teacher@test.com",
            password="password123",
            first_name="Jane",
            last_name="Doe",
        )
        UserRole.objects.create(
            user=self.teacher_user, school=self.school, role="teacher"
        )
        self.client = Client(SERVER_NAME="127.0.0.1")
        self.client.login(username="teacher@test.com", password="password123")

    def test_teacher_dashboard_returns_200(self):
        response = self.client.get(reverse("portals:teacher_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "portals/teacher_dashboard.html")

    def test_teacher_dashboard_with_staff_profile(self):
        Staff.objects.create(
            school=self.school,
            user=self.teacher_user,
            employee_number="T001",
            first_name="Jane",
            last_name="Doe",
        )
        response = self.client.get(reverse("portals:teacher_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context["staff_profile"])

    def test_non_teacher_redirected_from_teacher_dashboard(self):
        student_user = User.objects.create_user(
            email="student@test.com",
            password="password123",
            first_name="S",
            last_name="U",
        )
        UserRole.objects.create(
            user=student_user, school=self.school, role="student"
        )
        self.client.login(username="student@test.com", password="password123")
        response = self.client.get(reverse("portals:teacher_dashboard"))
        self.assertRedirects(
            response, reverse("portals:dashboard"), fetch_redirect_response=False
        )


class StudentDashboardTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name="Test School", slug="testschool", is_active=True
        )
        self.student_user = User.objects.create_user(
            email="student@test.com",
            password="password123",
            first_name="Alice",
            last_name="Jones",
        )
        UserRole.objects.create(
            user=self.student_user, school=self.school, role="student"
        )
        self.student = Student.objects.create(
            school=self.school,
            user=self.student_user,
            student_id="S001",
            first_name="Alice",
            last_name="Jones",
        )
        self.client = Client(SERVER_NAME="127.0.0.1")
        self.client.login(username="student@test.com", password="password123")

    def test_student_dashboard_returns_200(self):
        response = self.client.get(reverse("portals:student_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "portals/student_dashboard.html")

    def test_student_dashboard_context_contains_student(self):
        response = self.client.get(reverse("portals:student_dashboard"))
        self.assertEqual(response.context["student"], self.student)

    def test_student_user_without_student_profile_renders_no_role(self):
        """If a user has student role but no Student object, show no_role page."""
        orphan = User.objects.create_user(
            email="orphan@test.com",
            password="password123",
            first_name="O",
            last_name="P",
        )
        UserRole.objects.create(user=orphan, school=self.school, role="student")
        self.client.login(username="orphan@test.com", password="password123")
        response = self.client.get(reverse("portals:student_dashboard"))
        self.assertTemplateUsed(response, "portals/no_role.html")

    def test_non_student_redirected_from_student_dashboard(self):
        teacher = User.objects.create_user(
            email="teacher@test.com",
            password="password123",
            first_name="T",
            last_name="U",
        )
        UserRole.objects.create(user=teacher, school=self.school, role="teacher")
        self.client.login(username="teacher@test.com", password="password123")
        response = self.client.get(reverse("portals:student_dashboard"))
        self.assertRedirects(
            response, reverse("portals:dashboard"), fetch_redirect_response=False
        )
