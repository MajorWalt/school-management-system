"""
Tests for the accounts app views:
  - login_view  (GET, POST success, POST failure, redirect if already logged in)
  - logout_view
"""
import datetime

from django.test import TestCase, Client
from django.urls import reverse

from accounts.models import User
from core.models import School


class AccountsViewTests(TestCase):
    """Tests for accounts login/logout views."""

    def setUp(self):
        # Middleware looks for first active school on 127.0.0.1
        self.school = School.objects.create(
            name="Test School", slug="testschool", is_active=True
        )
        self.user = User.objects.create_user(
            email="user@test.com",
            password="password123",
            first_name="Test",
            last_name="User",
        )
        self.client = Client(SERVER_NAME="127.0.0.1")
        self.login_url = reverse("accounts:login")
        self.logout_url = reverse("accounts:logout")

    # ── login_view GET ────────────────────────────────────────────────────

    def test_login_get_returns_200(self):
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/login.html")

    def test_login_get_redirects_authenticated_user(self):
        self.client.login(username="user@test.com", password="password123")
        response = self.client.get(self.login_url)
        self.assertRedirects(
            response,
            reverse("portals:dashboard"),
            fetch_redirect_response=False,
        )

    # ── login_view POST ───────────────────────────────────────────────────

    def test_login_post_valid_credentials_redirects_to_dashboard(self):
        response = self.client.post(
            self.login_url,
            {"email": "user@test.com", "password": "password123"},
        )
        self.assertRedirects(
            response,
            reverse("portals:dashboard"),
            fetch_redirect_response=False,
        )

    def test_login_post_valid_credentials_with_next_redirects(self):
        response = self.client.post(
            self.login_url + "?next=/students/",
            {"email": "user@test.com", "password": "password123"},
        )
        self.assertRedirects(response, "/students/", fetch_redirect_response=False)

    def test_login_post_invalid_credentials_returns_200_with_error(self):
        response = self.client.post(
            self.login_url,
            {"email": "user@test.com", "password": "wrongpassword"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/login.html")
        messages = list(response.context["messages"])
        self.assertTrue(
            any("Invalid email or password" in str(m) for m in messages),
            "Expected error message not found in response messages.",
        )

    def test_login_post_nonexistent_user_returns_200_with_error(self):
        response = self.client.post(
            self.login_url,
            {"email": "nobody@test.com", "password": "password123"},
        )
        self.assertEqual(response.status_code, 200)

    # ── logout_view ───────────────────────────────────────────────────────

    def test_logout_redirects_to_login(self):
        self.client.login(username="user@test.com", password="password123")
        response = self.client.get(self.logout_url)
        self.assertRedirects(
            response,
            self.login_url,
            fetch_redirect_response=False,
        )

    def test_logout_unauthenticated_still_redirects(self):
        """logout_view has no @login_required, so it always redirects."""
        response = self.client.get(self.logout_url)
        self.assertRedirects(
            response,
            self.login_url,
            fetch_redirect_response=False,
        )
