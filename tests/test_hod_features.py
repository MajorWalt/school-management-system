"""
Tests for Head of Department (HOD) features.

Tests the following functionality:
  - Staff model HOD fields (is_head_of_department, department_2)
  - HOD validation rules (cannot be HOD without department)
  - HOD form display and submission
  - HOD access to grades for their departments
  - HOD department management
"""

import datetime
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib import messages

from accounts.models import User, UserRole
from accounts.utils import is_admin
from core.models import School
from staff.models import Staff
from scheduling.models import Course, Section, AcademicYear, Form
from grades.models import GradeEntry, Evaluation
from grades.views import get_hod_departments, section_in_departments
from students.models import Student
from scheduling.models import Enrolment


class HODModelTests(TestCase):
    """Tests for Staff model HOD fields and validation."""

    def setUp(self):
        self.school = School.objects.create(name="Test School", slug="testschool", is_active=True)
        self.admin_user = User.objects.create_user(
            email="admin@test.com",
            password="password123",
            first_name="Admin",
            last_name="User",
        )
        UserRole.objects.create(user=self.admin_user, school=self.school, role="admin")

    def test_hod_field_default_is_false(self):
        """Test that is_head_of_department defaults to False."""
        staff = Staff.objects.create(
            school=self.school,
            employee_number="EMP001",
            first_name="Jane",
            last_name="Smith",
        )
        self.assertFalse(staff.is_head_of_department)

    def test_hod_with_department(self):
        """Test creating an HOD with a primary department."""
        staff = Staff.objects.create(
            school=self.school,
            employee_number="EMP002",
            first_name="John",
            last_name="Doe",
            department="Mathematics",
            is_head_of_department=True,
        )
        self.assertTrue(staff.is_head_of_department)
        self.assertEqual(staff.department, "Mathematics")

    def test_hod_with_two_departments(self):
        """Test creating an HOD with both primary and secondary departments."""
        staff = Staff.objects.create(
            school=self.school,
            employee_number="EMP003",
            first_name="Alice",
            last_name="Johnson",
            department="Mathematics",
            department_2="Natural Sciences",
            is_head_of_department=True,
        )
        staff.full_clean()  # Validate
        staff.save()
        self.assertTrue(staff.is_head_of_department)
        self.assertEqual(staff.department, "Mathematics")
        self.assertEqual(staff.department_2, "Natural Sciences")

    def test_hod_cannot_have_same_departments(self):
        """Test that primary and secondary departments must be different."""
        staff = Staff.objects.create(
            school=self.school,
            employee_number="EMP004",
            first_name="Bob",
            last_name="Brown",
            department="Mathematics",
            department_2="Mathematics",  # Same as primary
            is_head_of_department=True,
        )
        from django.core.exceptions import ValidationError

        with self.assertRaises(ValidationError) as cm:
            staff.full_clean()
        self.assertIn("department_2", cm.exception.error_dict)

    def test_hod_validation_error_without_department(self):
        """Test that HOD cannot be assigned without a primary department."""
        from django.db import IntegrityError
        from django.core.exceptions import ValidationError

        staff = Staff(
            school=self.school,
            employee_number="EMP005",
            first_name="Carol",
            last_name="White",
            is_head_of_department=True,
            # No department specified
        )
        # full_clean() should catch the validation error
        with self.assertRaises(ValidationError) as cm:
            staff.full_clean()
        self.assertIn("is_head_of_department", cm.exception.error_dict)

    def test_second_department_requires_first(self):
        """Test that department_2 cannot exist without department."""
        from django.core.exceptions import ValidationError

        staff = Staff(
            school=self.school,
            employee_number="EMP006",
            first_name="David",
            last_name="Green",
            department_2="English",
            # No primary department
        )
        # full_clean() should catch the validation error
        with self.assertRaises(ValidationError) as cm:
            staff.full_clean()
        self.assertIn("department_2", cm.exception.error_dict)

    def test_get_departments_method(self):
        """Test the get_departments helper method."""
        staff = Staff.objects.create(
            school=self.school,
            employee_number="EMP007",
            first_name="Emma",
            last_name="Black",
            department="Mathematics",
            department_2="Physical Education",
        )
        depts = staff.get_departments()
        self.assertEqual(len(depts), 2)
        self.assertIn("Mathematics", depts)
        self.assertIn("Physical Education", depts)

    def test_get_departments_single_dept(self):
        """Test get_departments with only primary department."""
        staff = Staff.objects.create(
            school=self.school,
            employee_number="EMP008",
            first_name="Frank",
            last_name="Gray",
            department="English",
        )
        depts = staff.get_departments()
        self.assertEqual(len(depts), 1)
        self.assertIn("English", depts)

    def test_get_departments_no_dept(self):
        """Test get_departments with no departments."""
        staff = Staff.objects.create(
            school=self.school,
            employee_number="EMP009",
            first_name="Grace",
            last_name="Purple",
        )
        depts = staff.get_departments()
        self.assertEqual(len(depts), 0)


class HODAccessControlTests(TestCase):
    """Tests for HOD access to grades and sections."""

    def setUp(self):
        self.school = School.objects.create(name="Test School", slug="testschool", is_active=True)
        self.admin_user = User.objects.create_user(
            email="admin@test.com",
            password="password123",
            first_name="Admin",
            last_name="User",
        )
        UserRole.objects.create(user=self.admin_user, school=self.school, role="admin")

        # Create a teacher who is also an HOD
        self.hod_user = User.objects.create_user(
            email="hod@test.com",
            password="password123",
            first_name="HOD",
            last_name="Teacher",
        )
        UserRole.objects.create(user=self.hod_user, school=self.school, role="teacher")

        self.hod_staff = Staff.objects.create(
            school=self.school,
            user=self.hod_user,
            employee_number="EMP100",
            first_name="HOD",
            last_name="Teacher",
            department="Mathematics",
            department_2="Natural Sciences",
            is_head_of_department=True,
        )

        # Create regular teacher without HOD status
        self.teacher_user = User.objects.create_user(
            email="teacher@test.com",
            password="password123",
            first_name="Regular",
            last_name="Teacher",
        )
        UserRole.objects.create(user=self.teacher_user, school=self.school, role="teacher")

        self.regular_teacher = Staff.objects.create(
            school=self.school,
            user=self.teacher_user,
            employee_number="EMP200",
            first_name="Regular",
            last_name="Teacher",
            department="English",
        )

        # Create academic year, form, and courses
        self.year = AcademicYear.objects.create(school=self.school, name="2024-2025", is_current=True)
        self.form = Form.objects.create(school=self.school, name="Form 1", order=1)

        # Create courses for different departments
        self.math_course = Course.objects.create(
            school=self.school,
            name="Mathematics",
            code="MATH",
            department="Mathematics",
        )
        self.science_course = Course.objects.create(
            school=self.school,
            name="Natural Sciences",
            code="SCI",
            department="Natural Sciences",
        )
        self.english_course = Course.objects.create(
            school=self.school,
            name="English",
            code="ENG",
            department="English",
        )

        # Create sections
        self.math_section = Section.objects.create(
            school=self.school,
            course=self.math_course,
            academic_year=self.year,
            form=self.form,
            term_number=1,
            teacher=self.regular_teacher,
        )

        self.science_section = Section.objects.create(
            school=self.school,
            course=self.science_course,
            academic_year=self.year,
            form=self.form,
            term_number=1,
            teacher=self.regular_teacher,
        )

        self.english_section = Section.objects.create(
            school=self.school,
            course=self.english_course,
            academic_year=self.year,
            form=self.form,
            term_number=1,
            teacher=self.regular_teacher,
        )

    def test_get_hod_departments_returns_empty_for_non_hod(self):
        """Test that non-HOD staff get no departments."""
        depts = get_hod_departments(self.regular_teacher)
        self.assertEqual(len(depts), 0)

    def test_get_hod_departments_returns_primary_department(self):
        """Test that HOD gets their primary department."""
        depts = get_hod_departments(self.hod_staff)
        # Since hod_staff has both department and department_2, should return 2
        self.assertEqual(len(depts), 2)
        self.assertIn("Mathematics", depts)

    def test_get_hod_departments_returns_both_departments(self):
        """Test that HOD gets both primary and secondary departments."""
        # Update HOD to be marked as HOD
        self.hod_staff.is_head_of_department = True
        self.hod_staff.save()
        depts = get_hod_departments(self.hod_staff)
        self.assertEqual(len(depts), 2)
        self.assertIn("Mathematics", depts)
        self.assertIn("Natural Sciences", depts)

    def test_section_in_departments_for_hod_department(self):
        """Test that section is recognized as in HOD's department."""
        hod_depts = get_hod_departments(self.hod_staff)
        # Math section is in Mathematics department which HOD heads
        result = section_in_departments(self.math_section, hod_depts)
        self.assertTrue(result)

    def test_section_not_in_departments_for_other_department(self):
        """Test that section outside HOD's departments is not accessible."""
        hod_depts = get_hod_departments(self.hod_staff)
        # English section is NOT in HOD's departments
        result = section_in_departments(self.english_section, hod_depts)
        self.assertFalse(result)

    def test_section_in_hod_second_department(self):
        """Test that section in HOD's secondary department is recognized."""
        hod_depts = get_hod_departments(self.hod_staff)
        # Science section is in Natural Sciences department (secondary)
        result = section_in_departments(self.science_section, hod_depts)
        self.assertTrue(result)

    def test_section_in_departments_empty_departments_list(self):
        """Test that empty department list returns False."""
        result = section_in_departments(self.math_section, [])
        self.assertFalse(result)


class HODFormTests(TestCase):
    """Tests for HOD form fields and submission."""

    def setUp(self):
        self.school = School.objects.create(name="Test School", slug="testschool", is_active=True)
        self.admin_user = User.objects.create_user(
            email="admin@test.com",
            password="password123",
            first_name="Admin",
            last_name="User",
        )
        UserRole.objects.create(user=self.admin_user, school=self.school, role="admin")
        self.client = Client(SERVER_NAME="127.0.0.1")
        self.client.login(username="admin@test.com", password="password123")

    def test_staff_form_includes_hod_checkbox(self):
        """Test that the staff form includes HOD checkbox."""
        response = self.client.get(reverse("staff:add"))
        self.assertEqual(response.status_code, 200)
        # Check for HOD field in form (may appear multiple times in HTML)
        self.assertContains(response, "is_head_of_department")
        self.assertContains(response, "Head of Department")

    def test_staff_form_includes_second_department(self):
        """Test that the staff form includes secondary department field."""
        response = self.client.get(reverse("staff:add"))
        self.assertEqual(response.status_code, 200)
        # Check for second department field
        self.assertContains(response, "department_2")

    def test_create_staff_as_hod_with_form_post(self):
        """Test creating an HOD through the form."""
        response = self.client.post(
            reverse("staff:add"),
            {
                "employee_number": "EMP_HOD",
                "first_name": "Head",
                "last_name": "Department",
                "department": "Mathematics",
                "is_head_of_department": "on",
                "active": True,
            },
        )
        self.assertRedirects(response, reverse("staff:list"), fetch_redirect_response=False)
        staff = Staff.objects.get(employee_number="EMP_HOD")
        self.assertTrue(staff.is_head_of_department)
        self.assertEqual(staff.department, "Mathematics")

    def test_create_staff_as_hod_with_two_departments(self):
        """Test creating an HOD with two departments through the form."""
        response = self.client.post(
            reverse("staff:add"),
            {
                "employee_number": "EMP_HOD2",
                "first_name": "Dual",
                "last_name": "Department",
                "department": "English",
                "department_2": "Modern Languages",
                "is_head_of_department": "on",
                "active": True,
            },
        )
        self.assertRedirects(response, reverse("staff:list"), fetch_redirect_response=False)
        staff = Staff.objects.get(employee_number="EMP_HOD2")
        self.assertTrue(staff.is_head_of_department)
        self.assertEqual(staff.department, "English")
        self.assertEqual(staff.department_2, "Modern Languages")

    def test_edit_staff_to_make_hod(self):
        """Test editing an existing staff member to make them HOD."""
        staff = Staff.objects.create(
            school=self.school,
            employee_number="EMP_CONVERT",
            first_name="Convert",
            last_name="Me",
            department="Social Studies",
        )
        response = self.client.post(
            reverse("staff:edit", kwargs={"pk": staff.pk}),
            {
                "employee_number": "EMP_CONVERT",
                "first_name": "Convert",
                "last_name": "Me",
                "department": "Social Studies",
                "is_head_of_department": "on",
                "active": True,
            },
        )
        self.assertRedirects(
            response,
            reverse("staff:detail", kwargs={"pk": staff.pk}),
            fetch_redirect_response=False,
        )
        staff.refresh_from_db()
        self.assertTrue(staff.is_head_of_department)


class HODViewTests(TestCase):
    """Tests for HOD-related views."""

    def setUp(self):
        self.school = School.objects.create(name="Test School", slug="testschool", is_active=True)
        self.admin_user = User.objects.create_user(
            email="admin@test.com",
            password="password123",
            first_name="Admin",
            last_name="User",
        )
        UserRole.objects.create(user=self.admin_user, school=self.school, role="admin")
        self.client = Client(SERVER_NAME="127.0.0.1")
        self.client.login(username="admin@test.com", password="password123")

    def test_staff_detail_shows_hod_status(self):
        """Test that staff detail page shows HOD status."""
        staff = Staff.objects.create(
            school=self.school,
            employee_number="EMP_DETAIL",
            first_name="Detail",
            last_name="Test",
            department="Mathematics",
            is_head_of_department=True,
        )
        response = self.client.get(reverse("staff:detail", kwargs={"pk": staff.pk}))
        self.assertEqual(response.status_code, 200)
        # Check that HOD status is displayed
        self.assertContains(response, "Head of Department")

    def test_staff_detail_shows_both_departments(self):
        """Test that both departments are shown for dual-department HOD."""
        staff = Staff.objects.create(
            school=self.school,
            employee_number="EMP_DUAL",
            first_name="Dual",
            last_name="Dept",
            department="Mathematics",
            department_2="Natural Sciences",
            is_head_of_department=True,
        )
        response = self.client.get(reverse("staff:detail", kwargs={"pk": staff.pk}))
        self.assertEqual(response.status_code, 200)
        # Check that both departments are displayed
        self.assertContains(response, "Mathematics")
        self.assertContains(response, "Natural Sciences")


class UtilityFunctionsTest(TestCase):
    """Tests for utility functions like is_admin."""

    def setUp(self):
        self.school = School.objects.create(name="Test School", slug="testschool", is_active=True)
        self.admin_user = User.objects.create_user(
            email="admin@test.com",
            password="password123",
            first_name="Admin",
            last_name="User",
        )
        UserRole.objects.create(user=self.admin_user, school=self.school, role="admin")

    def test_is_admin_with_admin_role(self):
        """Test is_admin returns True for admin user."""
        result = is_admin(self.admin_user, self.school)
        self.assertTrue(result)

    def test_is_admin_with_superuser(self):
        """Test is_admin returns True for superuser."""
        superuser = User.objects.create_superuser(
            email="super@test.com",
            password="password123",
        )
        result = is_admin(superuser, self.school)
        self.assertTrue(result)

    def test_is_admin_with_teacher_role(self):
        """Test is_admin returns False for teacher user."""
        teacher = User.objects.create_user(
            email="teacher@test.com",
            password="password123",
            first_name="Teacher",
            last_name="User",
        )
        UserRole.objects.create(user=teacher, school=self.school, role="teacher")
        result = is_admin(teacher, self.school)
        self.assertFalse(result)
