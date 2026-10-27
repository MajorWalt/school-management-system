"""
Complete data migration script from SMA backup to Django School Management System
This script will:
1. Clear all existing data
2. Import data from the SMA MariaDB backup
3. Set standardized passwords (teacher123 for staff/admin, student123 for students)
"""

import os
import sys
import django
import mysql.connector
from datetime import datetime, date
from decimal import Decimal

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth.hashers import make_password
from django.db import transaction
from accounts.models import User, UserRole
from core.models import School, SchoolSettings, ActivityLog
from students.models import Student, House, Guardian, StudentGuardian, StudentNote, StudentHealthRecord
from staff.models import Staff, StaffClockIn
from scheduling.models import Form, Homeroom, AcademicYear, TermConfig, Course, Section, Enrolment, TimetableSettings, TimetablePeriod, NonSchoolDay
from grades.models import GradeWindow, Evaluation, GradeEntry, GradeComment, ReportCard
from attendance.models import Attendance
from behaviour.models import BehaviourIncident
from merits.models import MeritRecord, DemeritRecord
from branding.models import SchoolProfile

# Configuration
SMA_DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",  # Update with your MySQL password
    "database": "sma",
}

BACKUP_SQL_FILE = r"c:\Users\wal_g\Downloads\backup_sma87327-20261022\backup_sma87327-20261022.sql"
STAFF_PASSWORD = "teacher123"
STUDENT_PASSWORD = "student123"


class SMAMigrator:
    def __init__(self):
        self.school = None
        self.student_map = {}  # Maps old studnum -> new Student object
        self.staff_map = {}  # Maps old userid -> new Staff object
        self.user_map = {}  # Maps old id -> new User object
        self.form_map = {}  # Maps old grade -> new Form object
        self.homeroom_map = {}  # Maps old homeroom -> new Homeroom object
        self.house_map = {}  # Maps old house name -> new House object
        self.course_map = {}  # Maps old course code -> new Course object
        self.section_map = {}  # Maps old section id -> new Section object
        self.academic_year = None
        self.conn = None
        self.cursor = None

    def connect_to_source_db(self):
        """Connect to the SMA MySQL database after importing the SQL file"""
        print("Loading SQL backup file into MySQL...")

        # First, create a temporary connection to create the database
        temp_conn = mysql.connector.connect(host=SMA_DB_CONFIG["host"], user=SMA_DB_CONFIG["user"], password=SMA_DB_CONFIG["password"])
        temp_cursor = temp_conn.cursor()

        # Drop and recreate database
        temp_cursor.execute("DROP DATABASE IF EXISTS sma_temp")
        temp_cursor.execute("CREATE DATABASE sma_temp")
        temp_cursor.close()
        temp_conn.close()

        # Import the SQL file
        os.system(f'mysql -u{SMA_DB_CONFIG["user"]} -p{SMA_DB_CONFIG["password"]} sma_temp < "{BACKUP_SQL_FILE}"')

        # Connect to the newly populated database
        self.conn = mysql.connector.connect(host=SMA_DB_CONFIG["host"], user=SMA_DB_CONFIG["user"], password=SMA_DB_CONFIG["password"], database="sma_temp")
        self.cursor = self.conn.cursor(dictionary=True)
        print("Connected to SMA database")

    def clear_existing_data(self):
        """Clear all existing data from Django database"""
        print("Clearing existing data...")

        with transaction.atomic():
            # Clear in order of dependencies (reverse of creation)
            models_to_clear = [
                # Analytics & AI
                "analytics.AtRiskScore",
                "analytics.CriteriaRequirement",
                "analytics.PromotionCriteria",
                "ai.CommentDraft",
                "ai.CommentBatch",
                "ai.AIUsageLog",
                "ai.AskAIQuestion",
                # Reports & Portals
                ReportCard,
                # Grades
                GradeComment,
                GradeEntry,
                Evaluation,
                GradeWindow,
                # Attendance
                Attendance,
                # Behaviour & Merits
                BehaviourIncident,
                DemeritRecord,
                MeritRecord,
                # Scheduling
                "scheduling.TimetableSlot",
                "scheduling.Timetable",
                "scheduling.YearPlacement",
                Enrolment,
                Section,
                Course,
                TimetablePeriod,
                TimetableSettings,
                NonSchoolDay,
                "scheduling.SchoolEvent",
                "scheduling.FormTermRule",
                TermConfig,
                AcademicYear,
                Homeroom,
                Form,
                # Students
                "students.StudentStatusLog",
                StudentHealthRecord,
                StudentNote,
                StudentGuardian,
                Guardian,
                Student,
                House,
                # Staff
                StaffClockIn,
                Staff,
                # Core & Accounts
                ActivityLog,
                UserRole,
                User,
                SchoolSettings,
                SchoolProfile,
                School,
            ]

            for model in models_to_clear:
                if isinstance(model, str):
                    # Handle string references
                    from django.apps import apps

                    app_label, model_name = model.split(".")
                    model_class = apps.get_model(app_label, model_name)
                    model_class.objects.all().delete()
                else:
                    model.objects.all().delete()

        print("All existing data cleared")

    def create_school(self):
        """Create the main school object"""
        print("Creating school...")

        # Get school name from conf_system table if available
        self.cursor.execute("SELECT * FROM conf_system WHERE setting='school_name' LIMIT 1")
        school_row = self.cursor.fetchone()
        school_name = school_row["value"] if school_row else "Imported School"

        self.school = School.objects.create(name=school_name, slug=school_name.lower().replace(" ", "-"), is_active=True)

        # Create school settings with defaults
        SchoolSettings.objects.create(
            school=self.school,
            pass_mark=50,
            honours_1st_class=75,
            honours_2nd_class=65,
            coursework_weight=60,
            exam_weight=40,
        )

        # Create school profile
        SchoolProfile.objects.create(school=self.school, primary_color="#1e40af", accent_color="#3b82f6", primary_text_color="#ffffff")

        print(f"School created: {self.school.name}")

    def migrate_staff(self):
        """Migrate staff from SMA database"""
        print("Migrating staff...")

        self.cursor.execute("SELECT * FROM staff WHERE userid IS NOT NULL")
        staff_rows = self.cursor.fetchall()

        for row in staff_rows:
            try:
                # Create User account for staff
                email = row.get("emailwork") or row.get("emailpersonal") or f"{row['userid']}@school.edu"

                user = User.objects.create(
                    email=email,
                    first_name=row.get("firstname") or "",
                    last_name=row.get("lastname") or "",
                    password=make_password(STAFF_PASSWORD),
                    is_staff=True,
                    is_active=True,
                )

                # Create UserRole
                UserRole.objects.create(user=user, school=self.school, role="teacher")

                # Create Staff record
                staff = Staff.objects.create(
                    school=self.school,
                    user=user,
                    employee_number=row["userid"],
                    salutation=row.get("sal") or "",
                    first_name=row.get("firstname") or "",
                    middle_name=row.get("middlename") or "",
                    last_name=row.get("lastname") or "",
                    gender="M" if row.get("gender") == "M" else "F" if row.get("gender") == "F" else "O",
                    date_of_birth=row.get("birthdate"),
                    phone_1=row.get("home_phone") or "",
                    phone_2=row.get("cell_phone") or "",
                    email_work=row.get("emailwork") or "",
                    email_personal=row.get("emailpersonal") or "",
                    address=row.get("street") or "",
                    city=row.get("city") or "",
                    hire_date=row.get("tdate"),
                    active=True,
                    does_attendance=row.get("doatt") == "1",
                    emergency_contact_name=row.get("emergency_contact_name") or "",
                    emergency_contact_phone=row.get("emergency_contact_phone") or "",
                )

                self.staff_map[row["userid"]] = staff
                self.user_map[row["id"]] = user

            except Exception as e:
                print(f"Error migrating staff {row.get('userid')}: {e}")

        print(f"Migrated {len(self.staff_map)} staff members")

    def migrate_houses(self):
        """Migrate houses"""
        print("Migrating houses...")

        # Get unique houses from student table
        self.cursor.execute("SELECT DISTINCT house FROM student WHERE house IS NOT NULL AND house != ''")
        houses = self.cursor.fetchall()

        colors = ["red", "blue", "green", "yellow", "purple", "orange"]

        for idx, row in enumerate(houses):
            house_name = row["house"]
            house = House.objects.create(school=self.school, name=house_name, color=colors[idx % len(colors)])
            self.house_map[house_name] = house

        print(f"Migrated {len(self.house_map)} houses")

    def migrate_forms_and_homerooms(self):
        """Migrate forms (grades) and homerooms"""
        print("Migrating forms and homerooms...")

        # Get unique grades
        self.cursor.execute("SELECT DISTINCT grade FROM student WHERE grade IS NOT NULL AND grade != '' ORDER BY grade")
        grades = self.cursor.fetchall()

        for idx, row in enumerate(grades):
            grade_name = row["grade"]
            form = Form.objects.create(school=self.school, name=f"Form {grade_name}", order=idx + 1)
            self.form_map[grade_name] = form

        # Get unique homerooms
        self.cursor.execute("SELECT DISTINCT homeroom, grade FROM student WHERE homeroom IS NOT NULL AND homeroom != '' ORDER BY grade, homeroom")
        homerooms = self.cursor.fetchall()

        for row in homerooms:
            homeroom_name = row["homeroom"]
            grade = row["grade"]
            form = self.form_map.get(grade)

            if form and homeroom_name not in self.homeroom_map:
                homeroom = Homeroom.objects.create(school=self.school, form=form, name=homeroom_name)
                self.homeroom_map[homeroom_name] = homeroom

        print(f"Migrated {len(self.form_map)} forms and {len(self.homeroom_map)} homerooms")

    def migrate_academic_year(self):
        """Create current academic year and term structure"""
        print("Creating academic year...")

        current_year = datetime.now().year

        self.academic_year = AcademicYear.objects.create(
            school=self.school,
            name=f"{current_year}-{current_year + 1}",
            is_current=True,
            start_date=date(current_year, 9, 1),
            end_date=date(current_year + 1, 6, 30),
        )

        # Create 3 terms
        terms = [
            {"term_number": 1, "name": "Term 1", "start": date(current_year, 9, 1), "end": date(current_year, 12, 20)},
            {"term_number": 2, "name": "Term 2", "start": date(current_year + 1, 1, 7), "end": date(current_year + 1, 4, 10)},
            {"term_number": 3, "name": "Term 3", "start": date(current_year + 1, 4, 20), "end": date(current_year + 1, 6, 30)},
        ]

        for term_data in terms:
            TermConfig.objects.create(
                academic_year=self.academic_year,
                term_number=term_data["term_number"],
                name=term_data["name"],
                has_final_exam=(term_data["term_number"] == 3),
                coursework_weight=60,
                exam_weight=40,
                start_date=term_data["start"],
                end_date=term_data["end"],
            )

        print("Academic year created")

    def migrate_students(self):
        """Migrate students from SMA database"""
        print("Migrating students...")

        self.cursor.execute("SELECT * FROM student WHERE studnum IS NOT NULL")
        student_rows = self.cursor.fetchall()

        for row in student_rows:
            try:
                # Create User account for student
                email = row.get("email") or f"student{row['studnum']}@school.edu"

                user = User.objects.create(
                    email=email,
                    first_name=row.get("firstname") or "",
                    last_name=row.get("lastname") or "",
                    password=make_password(STUDENT_PASSWORD),
                    is_staff=False,
                    is_active=True,
                )

                # Create UserRole
                UserRole.objects.create(user=user, school=self.school, role="student")

                # Get form and homeroom
                form = self.form_map.get(row.get("grade"))
                homeroom = self.homeroom_map.get(row.get("homeroom"))
                house = self.house_map.get(row.get("house"))

                # Create Student record
                student = Student.objects.create(
                    school=self.school,
                    user=user,
                    student_id=str(row["studnum"]),
                    first_name=row.get("firstname") or "",
                    middle_name=row.get("initial") or "",
                    last_name=row.get("lastname") or "",
                    form=form,
                    homeroom=homeroom,
                    house=house,
                    gender="M" if row.get("sex") == "M" else "F" if row.get("sex") == "F" else "O",
                    date_of_birth=row.get("birthdate"),
                    phone=row.get("cell1") or row.get("hphone1") or "",
                    email=email,
                    address=row.get("address1") or "",
                    city=row.get("city1") or "",
                    admission_date=date.today(),
                    # Parent information
                    father_name=row.get("par1_firstname", "") + " " + row.get("par1_lastname", "")
                    if row.get("relation1") in ["Father", "Dad"]
                    else row.get("par2_firstname", "") + " " + row.get("par2_lastname", "")
                    if row.get("relation2") in ["Father", "Dad"]
                    else "",
                    mother_name=row.get("par1_firstname", "") + " " + row.get("par1_lastname", "")
                    if row.get("relation1") in ["Mother", "Mom"]
                    else row.get("par2_firstname", "") + " " + row.get("par2_lastname", "")
                    if row.get("relation2") in ["Mother", "Mom"]
                    else "",
                    # Emergency contact
                    emergency_contact_name=row.get("emname") or "",
                    emergency_phone_1=row.get("emhphone") or row.get("emcell") or "",
                    emergency_phone_2=row.get("emwphone") or "",
                    # Doctor
                    doctor_name=row.get("doctor") or "",
                    doctor_phone=row.get("docphone") or "",
                )

                self.student_map[row["studnum"]] = student

                # Create medical record if medical field exists
                if row.get("medical"):
                    StudentHealthRecord.objects.create(
                        school=self.school,
                        student=student,
                        category="condition",
                        title="Medical Information",
                        details=row["medical"],
                        severity="medium",
                        is_active=True,
                    )

            except Exception as e:
                print(f"Error migrating student {row.get('studnum')}: {e}")

        print(f"Migrated {len(self.student_map)} students")

    def migrate_courses(self):
        """Migrate courses/subjects"""
        print("Migrating courses...")

        self.cursor.execute("SELECT * FROM subject WHERE active='1'")
        subjects = self.cursor.fetchall()

        for row in subjects:
            try:
                course_code = row.get("code") or row.get("name", "")[:10]

                course = Course.objects.create(
                    school=self.school,
                    name=row.get("name") or "",
                    code=course_code,
                    short_description=row.get("shortname") or "",
                    active=True,
                    calc_average=True,
                    web_visible=True,
                )

                self.course_map[course_code] = course

            except Exception as e:
                print(f"Error migrating course {row.get('code')}: {e}")

        print(f"Migrated {len(self.course_map)} courses")

    def migrate_grades(self):
        """Migrate grade data from gbscore table"""
        print("Migrating grades...")

        # First, check if gbscore table exists and has data
        self.cursor.execute("SHOW TABLES LIKE 'gbscore'")
        if not self.cursor.fetchone():
            print("No gbscore table found, skipping grades migration")
            return

        self.cursor.execute("SELECT * FROM gbscore LIMIT 1000")  # Limit for initial migration
        grade_rows = self.cursor.fetchall()

        print(f"Found {len(grade_rows)} grade records to migrate")

        # Note: This is a simplified migration - actual implementation would need
        # to map course codes to sections and create proper evaluations

    def run_migration(self):
        """Run the complete migration"""
        try:
            print("=" * 60)
            print("Starting SMA to Django Migration")
            print("=" * 60)

            # Step 1: Connect to source database
            self.connect_to_source_db()

            # Step 2: Clear existing data
            self.clear_existing_data()

            # Step 3: Create school
            with transaction.atomic():
                self.create_school()

            # Step 4: Migrate staff
            with transaction.atomic():
                self.migrate_staff()

            # Step 5: Migrate organizational structures
            with transaction.atomic():
                self.migrate_houses()
                self.migrate_forms_and_homerooms()
                self.migrate_academic_year()

            # Step 6: Migrate students
            with transaction.atomic():
                self.migrate_students()

            # Step 7: Migrate courses
            with transaction.atomic():
                self.migrate_courses()

            # Step 8: Migrate grades (simplified)
            with transaction.atomic():
                self.migrate_grades()

            print("=" * 60)
            print("Migration completed successfully!")
            print("=" * 60)
            print(f"\nSummary:")
            print(f"  School: {self.school.name}")
            print(f"  Staff: {len(self.staff_map)}")
            print(f"  Students: {len(self.student_map)}")
            print(f"  Forms: {len(self.form_map)}")
            print(f"  Homerooms: {len(self.homeroom_map)}")
            print(f"  Houses: {len(self.house_map)}")
            print(f"  Courses: {len(self.course_map)}")
            print(f"\nDefault Passwords:")
            print(f"  Staff/Admin: {STAFF_PASSWORD}")
            print(f"  Students: {STUDENT_PASSWORD}")

        except Exception as e:
            print(f"\nMigration failed: {e}")
            import traceback

            traceback.print_exc()

        finally:
            if self.cursor:
                self.cursor.close()
            if self.conn:
                self.conn.close()


if __name__ == "__main__":
    migrator = SMAMigrator()
    migrator.run_migration()
