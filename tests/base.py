"""
Shared test utilities and base classes for the school management system tests.

The TenantMiddleware resolves request.school by:
  - localhost/127.0.0.1  → first active School in the DB
  - subdomain            → slug match

All view tests use the Django test client against 127.0.0.1, so they rely on
the "first active school" shortcut.  setUp() must create a School with
is_active=True before making any requests.
"""
import datetime

from django.test import TestCase, Client

from accounts.models import User, UserRole
from core.models import School
from scheduling.models import (
    AcademicYear,
    Course,
    Enrolment,
    Form,
    Homeroom,
    Section,
    TermConfig,
)
from staff.models import Staff
from students.models import Student, StudentStatusLog


class SchoolTestCase(TestCase):
    """
    Base class that sets up a School and an admin User before each test.
    All HTTP requests are made to SERVER_NAME=127.0.0.1 so TenantMiddleware
    picks up self.school automatically.
    """

    def setUp(self):
        self.school = School.objects.create(
            name="Test School",
            slug="testschool",
            is_active=True,
        )

        self.admin_user = User.objects.create_user(
            email="admin@test.com",
            password="password123",
            first_name="Admin",
            last_name="User",
        )
        UserRole.objects.create(
            user=self.admin_user,
            school=self.school,
            role="admin",
        )

        self.client = Client(SERVER_NAME="127.0.0.1")
        self.client.login(username="admin@test.com", password="password123")

    # ── helpers ────────────────────────────────────────────────────────────

    def make_teacher_user(self, email="teacher@test.com"):
        user = User.objects.create_user(
            email=email,
            password="password123",
            first_name="Teacher",
            last_name="User",
        )
        UserRole.objects.create(user=user, school=self.school, role="teacher")
        return user

    def make_student_user(self, email="student@test.com"):
        user = User.objects.create_user(
            email=email,
            password="password123",
            first_name="Student",
            last_name="User",
        )
        UserRole.objects.create(user=user, school=self.school, role="student")
        return user

    def make_staff(self, user=None, employee_number="EMP001"):
        return Staff.objects.create(
            school=self.school,
            user=user,
            employee_number=employee_number,
            first_name="Jane",
            last_name="Smith",
        )

    def make_student(self, student_id="S001"):
        student = Student.objects.create(
            school=self.school,
            student_id=student_id,
            first_name="Alice",
            last_name="Jones",
            admission_date=datetime.date.today(),
        )
        StudentStatusLog.objects.create(
            student=student,
            status="enrolled",
            change_date=datetime.date.today(),
            changed_by=self.admin_user,
        )
        return student

    def make_academic_year(self, name="2024-2025", is_current=True):
        return AcademicYear.objects.create(
            school=self.school,
            name=name,
            is_current=is_current,
        )

    def make_form(self, name="Form 1"):
        return Form.objects.create(school=self.school, name=name, order=1)

    def make_course(self, name="Mathematics"):
        return Course.objects.create(school=self.school, name=name, code="MATH")

    def make_section(self, course=None, academic_year=None, form=None, term_number=1):
        course = course or self.make_course()
        academic_year = academic_year or self.make_academic_year()
        form = form or self.make_form()
        return Section.objects.create(
            school=self.school,
            course=course,
            academic_year=academic_year,
            term_number=term_number,
            form=form,
        )

    def make_term_config(self, academic_year=None, term_number=1):
        academic_year = academic_year or self.make_academic_year()
        return TermConfig.objects.create(
            academic_year=academic_year,
            term_number=term_number,
            name=f"Term {term_number}",
            has_final_exam=False,
            coursework_weight=100,
            exam_weight=0,
        )

    def make_enrolment(self, student=None, section=None):
        student = student or self.make_student()
        section = section or self.make_section()
        return Enrolment.objects.create(student=student, section=section)
