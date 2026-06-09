"""
Tests for the grades app views:
  - grade_section_select
  - grade_section_overview
  - grade_enrolment_detail (GET, POST)
  - grade_entry_delete
  - visibility_overview
  - visibility_set_school (GET, POST)
  - visibility_set_student (GET, POST)
  - report_card_list
  - report_card_generate
  - report_card_publish
  - report_card_detail
"""
import datetime

from django.test import TestCase, Client
from django.urls import reverse

from accounts.models import User, UserRole
from core.models import School
from grades.models import GradeEntry, GradeVisibilityRule, ReportCard
from scheduling.models import AcademicYear, Course, Enrolment, Form, Section, TermConfig
from students.models import Student, StudentStatusLog


class GradesViewTests(TestCase):
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
        self.term_config = TermConfig.objects.create(
            academic_year=self.year,
            term_number=1,
            name="Term 1",
            has_final_exam=False,
            coursework_weight=100,
            exam_weight=0,
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

    # ── grade_section_select ───────────────────────────────────────────────

    def test_grade_section_select_returns_200(self):
        response = self.client.get(reverse("grades:section_select"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "grades/section_select.html")

    # ── grade_section_overview ─────────────────────────────────────────────

    def test_grade_section_overview_returns_200(self):
        response = self.client.get(
            reverse("grades:section_overview", kwargs={"section_pk": self.section.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "grades/section_overview.html")

    def test_grade_section_overview_has_rows_context(self):
        response = self.client.get(
            reverse("grades:section_overview", kwargs={"section_pk": self.section.pk})
        )
        self.assertIn("rows", response.context)
        self.assertEqual(len(response.context["rows"]), 1)

    # ── grade_enrolment_detail ─────────────────────────────────────────────

    def test_enrolment_detail_get_returns_200(self):
        response = self.client.get(
            reverse(
                "grades:enrolment_detail",
                kwargs={"enrolment_pk": self.enrolment.pk},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "grades/enrolment_detail.html")

    def test_enrolment_detail_post_creates_grade_entry(self):
        response = self.client.post(
            reverse(
                "grades:enrolment_detail",
                kwargs={"enrolment_pk": self.enrolment.pk},
            ),
            {
                "category": "coursework",
                "title": "Assignment 1",
                "max_marks": 100,
                "marks_earned": 80,
                "weight": 1,
                "is_final_exam": False,
                "date": datetime.date.today().isoformat(),
            },
        )
        self.assertRedirects(
            response,
            reverse(
                "grades:enrolment_detail",
                kwargs={"enrolment_pk": self.enrolment.pk},
            ),
            fetch_redirect_response=False,
        )
        self.assertTrue(
            GradeEntry.objects.filter(
                enrolment=self.enrolment, title="Assignment 1"
            ).exists()
        )

    def test_enrolment_detail_post_invalid_rerenders(self):
        response = self.client.post(
            reverse(
                "grades:enrolment_detail",
                kwargs={"enrolment_pk": self.enrolment.pk},
            ),
            {"category": "", "title": "", "max_marks": -1},
        )
        self.assertEqual(response.status_code, 200)

    # ── grade_entry_delete ─────────────────────────────────────────────────

    def test_grade_entry_delete(self):
        entry = GradeEntry.objects.create(
            school=self.school,
            enrolment=self.enrolment,
            category="coursework",
            title="Test Entry",
            max_marks=100,
            marks_earned=70,
            weight=1,
            is_final_exam=False,
            date=datetime.date.today(),
            entered_by=self.admin_user,
        )
        response = self.client.get(
            reverse("grades:entry_delete", kwargs={"pk": entry.pk})
        )
        self.assertRedirects(
            response,
            reverse(
                "grades:enrolment_detail",
                kwargs={"enrolment_pk": self.enrolment.pk},
            ),
            fetch_redirect_response=False,
        )
        self.assertFalse(GradeEntry.objects.filter(pk=entry.pk).exists())

    # ── visibility ─────────────────────────────────────────────────────────

    def test_visibility_overview_returns_200(self):
        response = self.client.get(reverse("grades:visibility"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "grades/visibility_overview.html")

    def test_visibility_set_school_get_returns_200(self):
        response = self.client.get(reverse("grades:visibility_school"))
        self.assertEqual(response.status_code, 200)

    def test_visibility_set_school_post_creates_rule(self):
        response = self.client.post(
            reverse("grades:visibility_school"),
            {"is_visible": True, "reason": "Term ended"},
        )
        self.assertRedirects(
            response, reverse("grades:visibility"), fetch_redirect_response=False
        )
        self.assertTrue(
            GradeVisibilityRule.objects.filter(
                school=self.school, student__isnull=True, is_visible=True
            ).exists()
        )

    def test_visibility_set_school_post_updates_existing_rule(self):
        GradeVisibilityRule.objects.create(
            school=self.school,
            student=None,
            is_visible=True,
            reason="Initial",
            set_by=self.admin_user,
        )
        self.client.post(
            reverse("grades:visibility_school"),
            {"is_visible": False, "reason": "Updated"},
        )
        rule = GradeVisibilityRule.objects.get(
            school=self.school, student__isnull=True
        )
        self.assertFalse(rule.is_visible)

    def test_visibility_set_student_get_returns_200(self):
        response = self.client.get(
            reverse(
                "grades:visibility_student",
                kwargs={"student_pk": self.student.pk},
            )
        )
        self.assertEqual(response.status_code, 200)

    def test_visibility_set_student_post_creates_rule(self):
        response = self.client.post(
            reverse(
                "grades:visibility_student",
                kwargs={"student_pk": self.student.pk},
            ),
            {"is_visible": True, "reason": "Requested by parent"},
        )
        self.assertRedirects(
            response, reverse("grades:visibility"), fetch_redirect_response=False
        )
        self.assertTrue(
            GradeVisibilityRule.objects.filter(
                school=self.school, student=self.student
            ).exists()
        )

    # ── report cards ───────────────────────────────────────────────────────

    def test_report_card_list_returns_200(self):
        response = self.client.get(reverse("grades:report_card_list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "grades/report_card_list.html")

    def test_report_card_generate_creates_draft(self):
        # Add a grade entry so compute_term_grade returns something
        GradeEntry.objects.create(
            school=self.school,
            enrolment=self.enrolment,
            category="coursework",
            title="Quiz 1",
            max_marks=100,
            marks_earned=75,
            weight=1,
            is_final_exam=False,
            date=datetime.date.today(),
            entered_by=self.admin_user,
        )
        response = self.client.get(
            reverse(
                "grades:report_card_generate",
                kwargs={"section_pk": self.section.pk},
            )
        )
        self.assertRedirects(
            response,
            reverse("grades:report_card_list"),
            fetch_redirect_response=False,
        )
        self.assertTrue(
            ReportCard.objects.filter(
                school=self.school,
                student=self.student,
                academic_year=self.year,
                term_number=1,
                status="draft",
            ).exists()
        )

    def test_report_card_publish_sets_published(self):
        rc = ReportCard.objects.create(
            school=self.school,
            student=self.student,
            academic_year=self.year,
            term_number=1,
            gpa=80,
            status="draft",
            generated_by=self.admin_user,
        )
        response = self.client.get(
            reverse("grades:report_card_publish", kwargs={"pk": rc.pk})
        )
        self.assertRedirects(
            response,
            reverse("grades:report_card_list"),
            fetch_redirect_response=False,
        )
        rc.refresh_from_db()
        self.assertEqual(rc.status, "published")

    def test_report_card_detail_returns_200(self):
        rc = ReportCard.objects.create(
            school=self.school,
            student=self.student,
            academic_year=self.year,
            term_number=1,
            gpa=80,
            status="published",
            generated_by=self.admin_user,
        )
        response = self.client.get(
            reverse("grades:report_card_detail", kwargs={"pk": rc.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "grades/report_card_detail.html")
