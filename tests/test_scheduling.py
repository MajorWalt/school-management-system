"""
Tests for the scheduling app views:
  - year_list / year_add / year_edit
  - term_add / term_edit
  - rule_add / rule_edit
  - non_school_day_list / non_school_day_add / non_school_day_delete
  - course_list / course_add / course_edit
  - section_list / section_add / section_detail / section_edit
  - enrol_student / enrolment_remove
"""
import datetime

from django.test import TestCase, Client
from django.urls import reverse

from accounts.models import User, UserRole
from core.models import School
from scheduling.models import (
    AcademicYear,
    Course,
    Enrolment,
    Form,
    FormTermRule,
    NonSchoolDay,
    Section,
    TermConfig,
)
from students.models import Student, StudentStatusLog


class SchedulingViewTests(TestCase):
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

    # ── Academic Years ─────────────────────────────────────────────────────

    def test_year_list_returns_200(self):
        response = self.client.get(reverse("scheduling:year_list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "scheduling/year_list.html")

    def test_year_add_get_returns_200(self):
        response = self.client.get(reverse("scheduling:year_add"))
        self.assertEqual(response.status_code, 200)

    def test_year_add_post_valid_creates_year(self):
        response = self.client.post(
            reverse("scheduling:year_add"),
            {"name": "2025-2026", "is_current": False},
        )
        self.assertRedirects(
            response, reverse("scheduling:year_list"), fetch_redirect_response=False
        )
        self.assertTrue(
            AcademicYear.objects.filter(
                school=self.school, name="2025-2026"
            ).exists()
        )

    def test_year_edit_get_returns_200(self):
        response = self.client.get(
            reverse("scheduling:year_edit", kwargs={"pk": self.year.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_year_edit_post_updates_year(self):
        response = self.client.post(
            reverse("scheduling:year_edit", kwargs={"pk": self.year.pk}),
            {"name": "2024-2025", "is_current": False},
        )
        self.assertRedirects(
            response, reverse("scheduling:year_list"), fetch_redirect_response=False
        )
        self.year.refresh_from_db()
        self.assertFalse(self.year.is_current)

    # ── Term Configs ───────────────────────────────────────────────────────

    def test_term_add_get_returns_200(self):
        response = self.client.get(
            reverse("scheduling:term_add", kwargs={"year_pk": self.year.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_term_add_post_creates_term_config(self):
        response = self.client.post(
            reverse("scheduling:term_add", kwargs={"year_pk": self.year.pk}),
            {
                "term_number": 1,
                "name": "Term 1",
                "has_final_exam": False,
                "coursework_weight": 100,
                "exam_weight": 0,
            },
        )
        self.assertRedirects(
            response, reverse("scheduling:year_list"), fetch_redirect_response=False
        )
        self.assertTrue(
            TermConfig.objects.filter(
                academic_year=self.year, term_number=1
            ).exists()
        )

    def test_term_edit_get_returns_200(self):
        term = TermConfig.objects.create(
            academic_year=self.year,
            term_number=2,
            name="Term 2",
            has_final_exam=False,
            coursework_weight=100,
            exam_weight=0,
        )
        response = self.client.get(
            reverse(
                "scheduling:term_edit",
                kwargs={"year_pk": self.year.pk, "pk": term.pk},
            )
        )
        self.assertEqual(response.status_code, 200)

    # ── Form Term Rules ────────────────────────────────────────────────────

    def test_rule_add_get_returns_200(self):
        response = self.client.get(
            reverse("scheduling:rule_add", kwargs={"year_pk": self.year.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_rule_add_post_creates_rule(self):
        response = self.client.post(
            reverse("scheduling:rule_add", kwargs={"year_pk": self.year.pk}),
            {
                "form": self.form.pk,
                "term_number": 1,
                "exam_label": "Mid Term",
                "exam_replaces_final": False,
                "notes": "",
            },
        )
        self.assertRedirects(
            response, reverse("scheduling:year_list"), fetch_redirect_response=False
        )
        self.assertTrue(
            FormTermRule.objects.filter(
                academic_year=self.year, form=self.form, term_number=1
            ).exists()
        )

    def test_rule_edit_get_returns_200(self):
        rule = FormTermRule.objects.create(
            academic_year=self.year,
            form=self.form,
            term_number=3,
            exam_label="Final",
        )
        response = self.client.get(
            reverse(
                "scheduling:rule_edit",
                kwargs={"year_pk": self.year.pk, "pk": rule.pk},
            )
        )
        self.assertEqual(response.status_code, 200)

    # ── Non-School Days ────────────────────────────────────────────────────

    def test_nsd_list_returns_200(self):
        response = self.client.get(reverse("scheduling:nsd_list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "scheduling/nsd_list.html")

    def test_nsd_add_get_returns_200(self):
        response = self.client.get(reverse("scheduling:nsd_add"))
        self.assertEqual(response.status_code, 200)

    def test_nsd_add_post_creates_nsd(self):
        response = self.client.post(
            reverse("scheduling:nsd_add"),
            {
                "date": "2025-12-25",
                "label": "Christmas",
                "type": "holiday",
            },
        )
        self.assertRedirects(
            response, reverse("scheduling:nsd_list"), fetch_redirect_response=False
        )
        self.assertTrue(
            NonSchoolDay.objects.filter(
                school=self.school, label="Christmas"
            ).exists()
        )

    def test_nsd_delete_removes_nsd(self):
        nsd = NonSchoolDay.objects.create(
            school=self.school,
            date=datetime.date(2025, 1, 1),
            label="New Year",
            type="holiday",
            created_by=self.admin_user,
        )
        response = self.client.get(
            reverse("scheduling:nsd_delete", kwargs={"pk": nsd.pk})
        )
        self.assertRedirects(
            response, reverse("scheduling:nsd_list"), fetch_redirect_response=False
        )
        self.assertFalse(NonSchoolDay.objects.filter(pk=nsd.pk).exists())

    # ── Courses ────────────────────────────────────────────────────────────

    def test_course_list_returns_200(self):
        response = self.client.get(reverse("scheduling:course_list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "scheduling/course_list.html")

    def test_course_add_get_returns_200(self):
        response = self.client.get(reverse("scheduling:course_add"))
        self.assertEqual(response.status_code, 200)

    def test_course_add_post_creates_course(self):
        response = self.client.post(
            reverse("scheduling:course_add"),
            {"name": "English", "code": "ENG", "active": True},
        )
        self.assertRedirects(
            response,
            reverse("scheduling:course_list"),
            fetch_redirect_response=False,
        )
        self.assertTrue(
            Course.objects.filter(school=self.school, name="English").exists()
        )

    def test_course_edit_get_returns_200(self):
        response = self.client.get(
            reverse("scheduling:course_edit", kwargs={"pk": self.course.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_course_edit_post_updates_course(self):
        response = self.client.post(
            reverse("scheduling:course_edit", kwargs={"pk": self.course.pk}),
            {"name": "Advanced Maths", "code": "AMATH", "active": True},
        )
        self.assertRedirects(
            response,
            reverse("scheduling:course_list"),
            fetch_redirect_response=False,
        )
        self.course.refresh_from_db()
        self.assertEqual(self.course.name, "Advanced Maths")

    # ── Sections ──────────────────────────────────────────────────────────

    def test_section_list_returns_200(self):
        response = self.client.get(reverse("scheduling:section_list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "scheduling/section_list.html")

    def test_section_list_filter_by_year(self):
        response = self.client.get(
            reverse("scheduling:section_list") + f"?year={self.year.pk}"
        )
        self.assertEqual(response.status_code, 200)

    def test_section_add_get_returns_200(self):
        response = self.client.get(reverse("scheduling:section_add"))
        self.assertEqual(response.status_code, 200)

    def test_section_add_post_creates_section(self):
        course2 = Course.objects.create(school=self.school, name="Science", code="SCI")
        response = self.client.post(
            reverse("scheduling:section_add"),
            {
                "course": course2.pk,
                "academic_year": self.year.pk,
                "term_number": 2,
                "form": self.form.pk,
                "room": "Room 3",
            },
        )
        new_section = Section.objects.filter(
            school=self.school, course=course2, term_number=2
        ).first()
        self.assertIsNotNone(new_section)
        self.assertRedirects(
            response,
            reverse("scheduling:section_detail", kwargs={"pk": new_section.pk}),
            fetch_redirect_response=False,
        )

    def test_section_detail_returns_200(self):
        response = self.client.get(
            reverse("scheduling:section_detail", kwargs={"pk": self.section.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "scheduling/section_detail.html")

    def test_section_edit_get_returns_200(self):
        response = self.client.get(
            reverse("scheduling:section_edit", kwargs={"pk": self.section.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_section_edit_post_updates_section(self):
        response = self.client.post(
            reverse("scheduling:section_edit", kwargs={"pk": self.section.pk}),
            {
                "course": self.course.pk,
                "academic_year": self.year.pk,
                "term_number": 1,
                "form": self.form.pk,
                "room": "Room 99",
            },
        )
        self.assertRedirects(
            response,
            reverse("scheduling:section_detail", kwargs={"pk": self.section.pk}),
            fetch_redirect_response=False,
        )
        self.section.refresh_from_db()
        self.assertEqual(self.section.room, "Room 99")

    # ── Enrolments ─────────────────────────────────────────────────────────

    def test_enrol_student_get_returns_200(self):
        response = self.client.get(
            reverse("scheduling:enrol", kwargs={"section_pk": self.section.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_enrol_student_post_creates_enrolment(self):
        response = self.client.post(
            reverse(
                "scheduling:enrol", kwargs={"section_pk": self.section.pk}
            ),
            {"student": self.student.pk, "section": self.section.pk},
        )
        self.assertRedirects(
            response,
            reverse("scheduling:section_detail", kwargs={"pk": self.section.pk}),
            fetch_redirect_response=False,
        )
        self.assertTrue(
            Enrolment.objects.filter(
                student=self.student, section=self.section
            ).exists()
        )

    def test_enrolment_remove_deletes_enrolment(self):
        enrolment = Enrolment.objects.create(
            student=self.student, section=self.section
        )
        response = self.client.get(
            reverse("scheduling:enrolment_remove", kwargs={"pk": enrolment.pk})
        )
        self.assertRedirects(
            response,
            reverse("scheduling:section_detail", kwargs={"pk": self.section.pk}),
            fetch_redirect_response=False,
        )
        self.assertFalse(Enrolment.objects.filter(pk=enrolment.pk).exists())
