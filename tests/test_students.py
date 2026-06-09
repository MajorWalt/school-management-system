"""
Tests for the students app views:
  - student_list    (GET, search, status filter)
  - student_add     (GET, POST valid)
  - student_detail  (GET, 404)
  - student_edit    (GET, POST valid)
  - student_status_change (GET, POST)
  - guardian_add    (GET, POST)
"""
import datetime

from django.test import TestCase, Client
from django.urls import reverse

from accounts.models import User, UserRole
from core.models import School
from students.models import Guardian, Student, StudentGuardian, StudentStatusLog


class StudentViewTests(TestCase):
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

        self.student = Student.objects.create(
            school=self.school,
            student_id="S001",
            first_name="Alice",
            last_name="Jones",
            admission_date=datetime.date.today(),
        )
        StudentStatusLog.objects.create(
            student=self.student,
            status="enrolled",
            change_date=datetime.date.today(),
            changed_by=self.admin_user,
        )

    # ── student_list ───────────────────────────────────────────────────────

    def test_student_list_requires_login(self):
        client = Client(SERVER_NAME="127.0.0.1")
        response = client.get(reverse("students:list"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])

    def test_student_list_returns_200(self):
        response = self.client.get(reverse("students:list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "students/student_list.html")

    def test_student_list_shows_enrolled_by_default(self):
        response = self.client.get(reverse("students:list"))
        self.assertContains(response, "Alice")

    def test_student_list_search_by_first_name(self):
        response = self.client.get(reverse("students:list") + "?q=Alice")
        self.assertContains(response, "Alice")

    def test_student_list_search_no_results(self):
        response = self.client.get(reverse("students:list") + "?q=ZZZNotFound")
        self.assertNotContains(response, "Alice")

    def test_student_list_status_filter_all(self):
        response = self.client.get(reverse("students:list") + "?status=all")
        self.assertEqual(response.status_code, 200)

    def test_student_list_status_filter_withdrawn(self):
        """Student with enrolled status should not appear in withdrawn filter."""
        response = self.client.get(reverse("students:list") + "?status=withdrawn")
        self.assertNotContains(response, "Alice")

    # ── student_add ────────────────────────────────────────────────────────

    def test_student_add_get_returns_200(self):
        response = self.client.get(reverse("students:add"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "students/student_form.html")

    def test_student_add_post_valid_creates_student_and_status_log(self):
        response = self.client.post(
            reverse("students:add"),
            {
                "student_id": "S002",
                "first_name": "Bob",
                "last_name": "Smith",
                "admission_date": datetime.date.today().isoformat(),
            },
        )
        self.assertTrue(
            Student.objects.filter(school=self.school, student_id="S002").exists()
        )
        student = Student.objects.get(school=self.school, student_id="S002")
        self.assertTrue(
            StudentStatusLog.objects.filter(
                student=student, status="enrolled"
            ).exists()
        )
        self.assertRedirects(
            response,
            reverse("students:detail", kwargs={"pk": student.pk}),
            fetch_redirect_response=False,
        )

    def test_student_add_post_invalid_rerenders_form(self):
        response = self.client.post(
            reverse("students:add"),
            {"student_id": "", "first_name": "", "last_name": ""},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "students/student_form.html")

    # ── student_detail ─────────────────────────────────────────────────────

    def test_student_detail_returns_200(self):
        response = self.client.get(
            reverse("students:detail", kwargs={"pk": self.student.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "students/student_detail.html")

    def test_student_detail_404_wrong_school(self):
        other_school = School.objects.create(
            name="Other", slug="other", is_active=False
        )
        other_student = Student.objects.create(
            school=other_school,
            student_id="S999",
            first_name="Ghost",
            last_name="Student",
        )
        response = self.client.get(
            reverse("students:detail", kwargs={"pk": other_student.pk})
        )
        self.assertEqual(response.status_code, 404)

    # ── student_edit ───────────────────────────────────────────────────────

    def test_student_edit_get_returns_200(self):
        response = self.client.get(
            reverse("students:edit", kwargs={"pk": self.student.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "students/student_form.html")

    def test_student_edit_post_valid_updates_student(self):
        response = self.client.post(
            reverse("students:edit", kwargs={"pk": self.student.pk}),
            {
                "student_id": "S001",
                "first_name": "Alice",
                "last_name": "Updated",
                "admission_date": datetime.date.today().isoformat(),
            },
        )
        self.assertRedirects(
            response,
            reverse("students:detail", kwargs={"pk": self.student.pk}),
            fetch_redirect_response=False,
        )
        self.student.refresh_from_db()
        self.assertEqual(self.student.last_name, "Updated")

    # ── student_status_change ──────────────────────────────────────────────

    def test_status_change_get_returns_200(self):
        response = self.client.get(
            reverse("students:status", kwargs={"pk": self.student.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "students/student_status_form.html")

    def test_status_change_post_creates_log_entry(self):
        # Use a future date so this log sorts after the initial "enrolled" log
        future_date = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
        response = self.client.post(
            reverse("students:status", kwargs={"pk": self.student.pk}),
            {
                "status": "withdrawn",
                "change_date": future_date,
                "reason": "Family moved away",
            },
        )
        self.assertRedirects(
            response,
            reverse("students:detail", kwargs={"pk": self.student.pk}),
            fetch_redirect_response=False,
        )
        self.student.refresh_from_db()
        self.assertEqual(self.student.current_status(), "withdrawn")

    # ── guardian_add ───────────────────────────────────────────────────────

    def test_guardian_add_get_returns_200(self):
        response = self.client.get(
            reverse("students:guardian_add", kwargs={"student_pk": self.student.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "students/guardian_form.html")

    def test_guardian_add_post_creates_guardian_and_link(self):
        response = self.client.post(
            reverse("students:guardian_add", kwargs={"student_pk": self.student.pk}),
            {
                "first_name": "Mary",
                "last_name": "Jones",
                "relationship": "mother",
                "is_primary": True,
                "can_pickup": True,
            },
        )
        self.assertRedirects(
            response,
            reverse("students:detail", kwargs={"pk": self.student.pk}),
            fetch_redirect_response=False,
        )
        self.assertTrue(
            Guardian.objects.filter(
                school=self.school, first_name="Mary"
            ).exists()
        )
        guardian = Guardian.objects.get(school=self.school, first_name="Mary")
        self.assertTrue(
            StudentGuardian.objects.filter(
                student=self.student, guardian=guardian
            ).exists()
        )
