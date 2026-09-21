from django.core.management.base import BaseCommand
from django.db import transaction
from accounts.models import User
from staff.models import Staff
from students.models import Student, Guardian, StudentGuardian, StudentStatusLog, StudentNote, House
from scheduling.models import (
    Course,
    Section,
    Enrolment,
    Form,
    Homeroom,
    AcademicYear,
    TermConfig,
    FormTermRule,
    NonSchoolDay,
    TimetableSettings,
    TimetablePeriod,
    Timetable,
    TimetableSlot,
    YearPlacement,
)
from grades.models import GradeWindow, Evaluation, GradeEntry, GradeComment, ReportCard, GradeVisibilityRule
from attendance.models import Attendance
from merits.models import MeritRecord, DemeritRecord


class Command(BaseCommand):
    help = "Delete all courses, students, grades, and teachers (except wgreenaway@smadominica.com)"

    def handle(self, *args, **options):
        protected_email = "wgreenaway@smadominica.com"

        try:
            protected_user = User.objects.get(email=protected_email)
            self.stdout.write(self.style.SUCCESS(f"Protected user found: {protected_user}"))
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Protected user {protected_email} not found!"))
            return

        with transaction.atomic():
            # Step 1: Delete all GRADES data
            self.stdout.write("\n=== Deleting Grades Data ===")

            report_card_count = ReportCard.objects.count()
            ReportCard.objects.all().delete()
            self.stdout.write(f"Deleted {report_card_count} report cards")

            grade_comment_count = GradeComment.objects.count()
            GradeComment.objects.all().delete()
            self.stdout.write(f"Deleted {grade_comment_count} grade comments")

            grade_entry_count = GradeEntry.objects.count()
            GradeEntry.objects.all().delete()
            self.stdout.write(f"Deleted {grade_entry_count} grade entries")

            evaluation_count = Evaluation.objects.count()
            Evaluation.objects.all().delete()
            self.stdout.write(f"Deleted {evaluation_count} evaluations")

            grade_window_count = GradeWindow.objects.count()
            GradeWindow.objects.all().delete()
            self.stdout.write(f"Deleted {grade_window_count} grade windows")

            grade_visibility_count = GradeVisibilityRule.objects.count()
            GradeVisibilityRule.objects.all().delete()
            self.stdout.write(f"Deleted {grade_visibility_count} grade visibility rules")

            # Step 2: Delete ATTENDANCE and MERITS data (related to students)
            self.stdout.write("\n=== Deleting Attendance & Merits Data ===")

            attendance_count = Attendance.objects.count()
            Attendance.objects.all().delete()
            self.stdout.write(f"Deleted {attendance_count} attendance records")

            merit_count = MeritRecord.objects.count()
            MeritRecord.objects.all().delete()
            self.stdout.write(f"Deleted {merit_count} merit records")

            demerit_count = DemeritRecord.objects.count()
            DemeritRecord.objects.all().delete()
            self.stdout.write(f"Deleted {demerit_count} demerit records")

            # Step 3: Delete SCHEDULING data (courses and enrolments)
            self.stdout.write("\n=== Deleting Scheduling Data ===")

            timetable_slot_count = TimetableSlot.objects.count()
            TimetableSlot.objects.all().delete()
            self.stdout.write(f"Deleted {timetable_slot_count} timetable slots")

            timetable_count = Timetable.objects.count()
            Timetable.objects.all().delete()
            self.stdout.write(f"Deleted {timetable_count} timetables")

            year_placement_count = YearPlacement.objects.count()
            YearPlacement.objects.all().delete()
            self.stdout.write(f"Deleted {year_placement_count} year placements")

            enrolment_count = Enrolment.objects.count()
            Enrolment.objects.all().delete()
            self.stdout.write(f"Deleted {enrolment_count} enrolments")

            section_count = Section.objects.count()
            Section.objects.all().delete()
            self.stdout.write(f"Deleted {section_count} sections")

            course_count = Course.objects.count()
            Course.objects.all().delete()
            self.stdout.write(f"Deleted {course_count} courses")

            non_school_day_count = NonSchoolDay.objects.count()
            NonSchoolDay.objects.all().delete()
            self.stdout.write(f"Deleted {non_school_day_count} non-school days")

            form_term_rule_count = FormTermRule.objects.count()
            FormTermRule.objects.all().delete()
            self.stdout.write(f"Deleted {form_term_rule_count} form term rules")

            term_config_count = TermConfig.objects.count()
            TermConfig.objects.all().delete()
            self.stdout.write(f"Deleted {term_config_count} term configs")

            timetable_period_count = TimetablePeriod.objects.count()
            TimetablePeriod.objects.all().delete()
            self.stdout.write(f"Deleted {timetable_period_count} timetable periods")

            timetable_settings_count = TimetableSettings.objects.count()
            TimetableSettings.objects.all().delete()
            self.stdout.write(f"Deleted {timetable_settings_count} timetable settings")

            academic_year_count = AcademicYear.objects.count()
            AcademicYear.objects.all().delete()
            self.stdout.write(f"Deleted {academic_year_count} academic years")

            # Step 4: Delete STUDENTS data
            self.stdout.write("\n=== Deleting Students Data ===")

            student_note_count = StudentNote.objects.count()
            StudentNote.objects.all().delete()
            self.stdout.write(f"Deleted {student_note_count} student notes")

            student_status_log_count = StudentStatusLog.objects.count()
            StudentStatusLog.objects.all().delete()
            self.stdout.write(f"Deleted {student_status_log_count} student status logs")

            student_guardian_count = StudentGuardian.objects.count()
            StudentGuardian.objects.all().delete()
            self.stdout.write(f"Deleted {student_guardian_count} student-guardian relationships")

            student_count = Student.objects.count()
            Student.objects.all().delete()
            self.stdout.write(f"Deleted {student_count} students")

            guardian_count = Guardian.objects.count()
            Guardian.objects.all().delete()
            self.stdout.write(f"Deleted {guardian_count} guardians")

            house_count = House.objects.count()
            House.objects.all().delete()
            self.stdout.write(f"Deleted {house_count} houses")

            # Delete homerooms and forms
            homeroom_count = Homeroom.objects.count()
            Homeroom.objects.all().delete()
            self.stdout.write(f"Deleted {homeroom_count} homerooms")

            form_count = Form.objects.count()
            Form.objects.all().delete()
            self.stdout.write(f"Deleted {form_count} forms")

            # Step 5: Delete TEACHERS (except protected user)
            self.stdout.write("\n=== Deleting Teachers Data ===")

            # Get staff members to delete (all except the protected user's staff profile)
            staff_to_delete = Staff.objects.exclude(user=protected_user)
            staff_count = staff_to_delete.count()
            staff_to_delete.delete()
            self.stdout.write(f"Deleted {staff_count} staff members (kept staff profile for {protected_email})")

            # Delete user accounts (except protected user)
            users_to_delete = User.objects.exclude(email=protected_email)
            user_count = users_to_delete.count()
            users_to_delete.delete()
            self.stdout.write(f"Deleted {user_count} user accounts (kept {protected_email})")

            self.stdout.write(self.style.SUCCESS("\n=== Deletion Complete ==="))
            self.stdout.write(self.style.SUCCESS(f"All data deleted except user: {protected_email}"))
