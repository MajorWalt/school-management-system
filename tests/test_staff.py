"""
Tests for the staff app views:
  - staff_list    (GET, search)
  - staff_add     (GET, POST valid, POST invalid)
  - staff_detail  (GET, 404 for wrong school)
  - staff_edit    (GET, POST valid) — also covers the bug fix
  - staff_deactivate / staff_reactivate (GET)
"""
from django.test import TestCase, Client
from django.urls import reverse

from accounts.models import User, UserRole
from core.models import School
from staff.models import Staff


class StaffViewTests(TestCase):
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

    # ── unauthenticated access ─────────────────────────────────────────────

    def test_staff_list_requires_login(self):
        client = Client(SERVER_NAME="127.0.0.1")
        response = client.get(reverse("staff:list"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])

    # ── staff_list ─────────────────────────────────────────────────────────

    def test_staff_list_returns_200(self):
        response = self.client.get(reverse("staff:list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "staff/staff_list.html")

    def test_staff_list_shows_staff(self):
        response = self.client.get(reverse("staff:list"))
        self.assertContains(response, "Jane")

    def test_staff_list_search_by_first_name(self):
        response = self.client.get(reverse("staff:list") + "?q=Jane")
        self.assertContains(response, "Jane")

    def test_staff_list_search_no_results(self):
        response = self.client.get(reverse("staff:list") + "?q=ZZZNotFound")
        self.assertNotContains(response, "Jane")

    # ── staff_add ──────────────────────────────────────────────────────────

    def test_staff_add_get_returns_200(self):
        response = self.client.get(reverse("staff:add"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "staff/staff_form.html")

    def test_staff_add_post_valid_creates_staff(self):
        response = self.client.post(
            reverse("staff:add"),
            {
                "employee_number": "EMP002",
                "first_name": "Bob",
                "last_name": "Brown",
                "active": True,
            },
        )
        self.assertRedirects(
            response, reverse("staff:list"), fetch_redirect_response=False
        )
        self.assertTrue(
            Staff.objects.filter(
                school=self.school, employee_number="EMP002"
            ).exists()
        )

    def test_staff_add_post_invalid_rerenders_form(self):
        response = self.client.post(
            reverse("staff:add"),
            {"employee_number": "", "first_name": "", "last_name": ""},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "staff/staff_form.html")

    # ── staff_detail ───────────────────────────────────────────────────────

    def test_staff_detail_returns_200(self):
        response = self.client.get(
            reverse("staff:detail", kwargs={"pk": self.staff_member.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "staff/staff_detail.html")

    def test_staff_detail_404_for_wrong_school(self):
        other_school = School.objects.create(
            name="Other School", slug="otherschool", is_active=False
        )
        other_staff = Staff.objects.create(
            school=other_school,
            employee_number="EMP999",
            first_name="Ghost",
            last_name="Member",
        )
        response = self.client.get(
            reverse("staff:detail", kwargs={"pk": other_staff.pk})
        )
        self.assertEqual(response.status_code, 404)

    # ── staff_edit ─────────────────────────────────────────────────────────

    def test_staff_edit_get_returns_200(self):
        response = self.client.get(
            reverse("staff:edit", kwargs={"pk": self.staff_member.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "staff/staff_form.html")

    def test_staff_edit_post_valid_updates_staff(self):
        response = self.client.post(
            reverse("staff:edit", kwargs={"pk": self.staff_member.pk}),
            {
                "employee_number": "EMP001",
                "first_name": "Jane",
                "last_name": "Updated",
                "active": True,
            },
        )
        self.assertRedirects(
            response,
            reverse("staff:detail", kwargs={"pk": self.staff_member.pk}),
            fetch_redirect_response=False,
        )
        self.staff_member.refresh_from_db()
        self.assertEqual(self.staff_member.last_name, "Updated")

    def test_staff_edit_post_invalid_rerenders_form(self):
        response = self.client.post(
            reverse("staff:edit", kwargs={"pk": self.staff_member.pk}),
            {"employee_number": "", "first_name": "", "last_name": ""},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "staff/staff_form.html")

    # ── staff_deactivate / staff_reactivate ────────────────────────────────

    def test_staff_deactivate_sets_active_false(self):
        self.assertTrue(self.staff_member.active)
        response = self.client.get(
            reverse("staff:deactivate", kwargs={"pk": self.staff_member.pk})
        )
        self.assertRedirects(
            response, reverse("staff:list"), fetch_redirect_response=False
        )
        self.staff_member.refresh_from_db()
        self.assertFalse(self.staff_member.active)

    def test_staff_reactivate_sets_active_true(self):
        self.staff_member.active = False
        self.staff_member.save()
        response = self.client.get(
            reverse("staff:reactivate", kwargs={"pk": self.staff_member.pk})
        )
        self.assertRedirects(
            response, reverse("staff:list"), fetch_redirect_response=False
        )
        self.staff_member.refresh_from_db()
        self.assertTrue(self.staff_member.active)
