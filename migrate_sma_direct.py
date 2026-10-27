"""
Complete data migration script from SMA SQL backup to Django School Management System
This script will:
1. Clear all existing data
2. Parse and import data directly from the SQL backup file
3. Set standardized passwords (teacher123 for staff/admin, student123 for students)
"""

import os
import sys
import django
import re
from datetime import datetime, date
from decimal import Decimal

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth.hashers import make_password
from django.db import transaction
from accounts.models import User, UserRole
from core.models import School, SchoolSettings
from students.models import Student, House, Guardian, StudentGuardian, StudentHealthRecord
from staff.models import Staff
from scheduling.models import Form, Homeroom, AcademicYear, TermConfig
from branding.models import SchoolProfile

# Configuration
BACKUP_SQL_FILE = r"c:\Users\wal_g\Downloads\backup_sma87327-20261022\backup_sma87327-20261022.sql"
STAFF_PASSWORD = "teacher123"
STUDENT_PASSWORD = "student123"


class SQLParser:
    """Parse SQL INSERT statements from backup file"""

    @staticmethod
    def parse_insert_values(insert_statement):
        """Extract values from INSERT INTO statement"""
        # Find the VALUES clause
        values_match = re.search(r"VALUES\s+(.+);", insert_statement, re.DOTALL | re.IGNORECASE)
        if not values_match:
            return []

        values_str = values_match.group(1)
        rows = []

        # Split by '),(' to get individual rows
        # Handle the first '(' and last ')'
        values_str = values_str.strip()
        if values_str.startswith("("):
            values_str = values_str[1:]
        if values_str.endswith(")"):
            values_str = values_str[:-1]

        # Split on '),(' pattern
        row_strings = re.split(r"\),\s*\(", values_str)

        for row_str in row_strings:
            # Parse individual values - simpler approach
            values = []
            current_value = ""
            in_string = False
            i = 0

            while i < len(row_str):
                char = row_str[i]

                # Handle escaped characters
                if char == "\\" and i + 1 < len(row_str):
                    current_value += row_str[i + 1]
                    i += 2
                    continue

                # Handle string delimiters
                if char == "'":
                    if in_string:
                        # End of string - add value
                        values.append(current_value)
                        current_value = ""
                        in_string = False
                        # Skip to next comma
                        i += 1
                        while i < len(row_str) and row_str[i] != ",":
                            i += 1
                        i += 1
                        continue
                    else:
                        # Start of string
                        in_string = True
                        i += 1
                        continue

                # Handle commas outside strings
                if char == "," and not in_string:
                    # Value separator for non-string values
                    val = current_value.strip()
                    if val == "NULL" or val == "":
                        values.append(None)
                    else:
                        values.append(val)
                    current_value = ""
                    i += 1
                    continue

                # Add character to current value
                if in_string or char not in (" ", "\t", "\n", "\r"):
                    current_value += char

                i += 1

            # Add last value
            val = current_value.strip()
            if val == "NULL" or val == "":
                values.append(None)
            else:
                values.append(val)

            rows.append(values)

        return rows

    @staticmethod
    def get_table_data(sql_file, table_name):
        """Extract all INSERT data for a specific table"""
        print(f"Extracting data from table: {table_name}")
        rows = []
        current_insert = ""
        in_insert = False

        with open(sql_file, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()

                # Check if this is an INSERT for our table
                if line.startswith(f"INSERT INTO `{table_name}`"):
                    in_insert = True
                    current_insert = line

                    # Check if complete on one line
                    if line.endswith(";"):
                        rows.extend(SQLParser.parse_insert_values(current_insert))
                        current_insert = ""
                        in_insert = False
                elif in_insert:
                    current_insert += " " + line
                    if line.endswith(";"):
                        rows.extend(SQLParser.parse_insert_values(current_insert))
                        current_insert = ""
                        in_insert = False

        print(f"Extracted {len(rows)} rows from {table_name}")
        return rows


class SMADirectMigrator:
    def __init__(self):
        self.school = None
        self.student_map = {}
        self.staff_map = {}
        self.user_map = {}
        self.form_map = {}
        self.homeroom_map = {}
        self.house_map = {}
        self.academic_year = None

    def clear_existing_data(self):
        """Clear all existing data from Django database"""
        print("\n" + "=" * 60)
        print("CLEARING EXISTING DATA")
        print("=" * 60)

        with transaction.atomic():
            # Clear in order of dependencies
            print("Clearing students...")
            StudentHealthRecord.objects.all().delete()
            StudentGuardian.objects.all().delete()
            Guardian.objects.all().delete()
            Student.objects.all().delete()
            House.objects.all().delete()

            print("Clearing staff...")
            Staff.objects.all().delete()

            print("Clearing scheduling...")
            TermConfig.objects.all().delete()
            AcademicYear.objects.all().delete()
            Homeroom.objects.all().delete()
            Form.objects.all().delete()

            print("Clearing users...")
            UserRole.objects.all().delete()
            User.objects.all().delete()

            print("Clearing school...")
            SchoolSettings.objects.all().delete()
            SchoolProfile.objects.all().delete()
            School.objects.all().delete()

        print("✓ All existing data cleared\n")

    def safe_get(self, row, index, default=""):
        """Safely get value from row by index"""
        try:
            if index < len(row):
                value = row[index]
                return value if value is not None else default
            return default
        except:
            return default

    def parse_date(self, date_str):
        """Parse date string to date object"""
        if not date_str or date_str == "NULL":
            return None
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except:
            return None

    def create_school(self):
        """Create the main school object"""
        print("\n" + "=" * 60)
        print("CREATING SCHOOL")
        print("=" * 60)

        # Try to get school name from conf_system
        conf_data = SQLParser.get_table_data(BACKUP_SQL_FILE, "conf_system")
        school_name = "Imported School"

        for row in conf_data:
            if self.safe_get(row, 0) == "school_name":
                school_name = self.safe_get(row, 1, school_name)
                break

        self.school = School.objects.create(name=school_name, slug=school_name.lower().replace(" ", "-").replace(".", "")[:50], is_active=True)

        # Create school settings
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

        print(f"✓ School created: {self.school.name}\n")

    def migrate_staff(self):
        """Migrate staff from SQL backup"""
        print("\n" + "=" * 60)
        print("MIGRATING STAFF")
        print("=" * 60)

        staff_data = SQLParser.get_table_data(BACKUP_SQL_FILE, "staff")

        # Staff table structure (from CREATE TABLE):
        # 0: id, 1: sal, 2: lastname, 3: firstname, 4: middlename, 5: userid, 6: password,
        # 7: emailwork, 8: emailpersonal, 9: tdate, 10: doatt, ...

        staff_count = 0
        for row in staff_data:
            try:
                userid = self.safe_get(row, 5)
                if not userid or userid == "NULL":
                    continue

                lastname = self.safe_get(row, 2)
                firstname = self.safe_get(row, 3)

                if not lastname and not firstname:
                    continue

                # Create User account
                email = self.safe_get(row, 7) or self.safe_get(row, 8) or f"{userid}@school.edu"

                user = User.objects.create(
                    email=email, first_name=firstname[:150], last_name=lastname[:150], password=make_password(STAFF_PASSWORD), is_staff=True, is_active=True
                )

                # Create UserRole
                UserRole.objects.create(user=user, school=self.school, role="teacher")

                # Get gender
                gender_val = self.safe_get(row, 44, "O")  # Assuming gender is around index 44
                if gender_val == "M":
                    gender = "M"
                elif gender_val == "F":
                    gender = "F"
                else:
                    gender = "O"

                # Create Staff record
                staff = Staff.objects.create(
                    school=self.school,
                    user=user,
                    employee_number=userid[:50],
                    salutation=self.safe_get(row, 1)[:10],
                    first_name=firstname[:100],
                    middle_name=self.safe_get(row, 4)[:100],
                    last_name=lastname[:100],
                    gender=gender,
                    date_of_birth=self.parse_date(self.safe_get(row, 45)),
                    phone_1=self.safe_get(row, 12)[:20],
                    phone_2=self.safe_get(row, 13)[:20],
                    email_work=self.safe_get(row, 7)[:254],
                    email_personal=self.safe_get(row, 8)[:254],
                    address=self.safe_get(row, 14)[:200],
                    city=self.safe_get(row, 15)[:100],
                    hire_date=self.parse_date(self.safe_get(row, 9)),
                    active=True,
                    does_attendance=(self.safe_get(row, 10) == "1"),
                    emergency_contact_name=self.safe_get(row, 18)[:200],
                    emergency_contact_phone=self.safe_get(row, 19)[:20],
                )

                self.staff_map[userid] = staff
                staff_count += 1

            except Exception as e:
                print(f"  ⚠ Error migrating staff {self.safe_get(row, 5)}: {e}")

        print(f"✓ Migrated {staff_count} staff members\n")

    def migrate_houses(self):
        """Migrate houses from student data"""
        print("\n" + "=" * 60)
        print("MIGRATING HOUSES")
        print("=" * 60)

        student_data = SQLParser.get_table_data(BACKUP_SQL_FILE, "student")

        # Get unique houses
        houses = set()
        for row in student_data:
            house = self.safe_get(row, 13)  # house field
            if house and str(house) != "NULL":
                house = str(house).strip()
                if house:
                    houses.add(house)

        colors = ["red", "blue", "green", "yellow", "purple", "orange", "teal", "pink"]

        for idx, house_name in enumerate(sorted(houses)):
            house = House.objects.create(school=self.school, name=house_name[:100], color=colors[idx % len(colors)])
            self.house_map[house_name] = house

        print(f"✓ Migrated {len(self.house_map)} houses\n")

    def migrate_forms_and_homerooms(self):
        """Migrate forms (grades) and homerooms"""
        print("\n" + "=" * 60)
        print("MIGRATING FORMS AND HOMEROOMS")
        print("=" * 60)

        student_data = SQLParser.get_table_data(BACKUP_SQL_FILE, "student")

        # Get unique grades and homerooms
        grades = set()
        homerooms_data = {}  # grade -> set of homeroom names

        for row in student_data:
            grade = self.safe_get(row, 9)  # grade field
            homeroom = self.safe_get(row, 10)  # homeroom field

            # Check if grade is valid (not empty, not NULL, not whitespace)
            if grade and str(grade) != "NULL":
                grade = str(grade).strip()
                if grade:
                    grades.add(grade)

                    # Check homeroom
                    if homeroom and str(homeroom) != "NULL":
                        homeroom = str(homeroom).strip()
                        if homeroom:
                            if grade not in homerooms_data:
                                homerooms_data[grade] = set()
                            homerooms_data[grade].add(homeroom)

        # Create forms - convert grade 7=Form 1, grade 8=Form 2, etc.
        for grade_name in sorted(grades, key=lambda x: int(x) if x.isdigit() else 999):
            try:
                grade_num = int(grade_name)
                form_num = grade_num - 6  # Grade 7 = Form 1, Grade 8 = Form 2, etc.
                form = Form.objects.create(school=self.school, name=f"Form {form_num}"[:100], order=form_num)
            except ValueError:
                # Non-numeric grade
                form = Form.objects.create(school=self.school, name=f"Form {grade_name}"[:100], order=99)
            self.form_map[grade_name] = form

        # Create homerooms
        for grade, homeroom_names in homerooms_data.items():
            form = self.form_map.get(grade)
            if form:
                for homeroom_name in sorted(homeroom_names):
                    homeroom = Homeroom.objects.create(school=self.school, form=form, name=homeroom_name[:100])
                    self.homeroom_map[homeroom_name] = homeroom

        print(f"✓ Migrated {len(self.form_map)} forms")
        print(f"✓ Migrated {len(self.homeroom_map)} homerooms\n")

    def migrate_academic_year(self):
        """Create current academic year"""
        print("\n" + "=" * 60)
        print("CREATING ACADEMIC YEAR")
        print("=" * 60)

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

        print(f"✓ Academic year created: {self.academic_year.name}\n")

    def migrate_students(self):
        """Migrate students from SQL backup"""
        print("\n" + "=" * 60)
        print("MIGRATING STUDENTS")
        print("=" * 60)

        student_data = SQLParser.get_table_data(BACKUP_SQL_FILE, "student")

        # Student table structure (from CREATE TABLE):
        # 0: studid, 1: lastname, 2: firstname, 3: initial (middle), 4-7: alias/legal names,
        # 8: studnum, 9: grade, 10: homeroom, 11: sex, 12: birthdate, 13: house,
        # 14: healthid, 15: ethnic, 16: treaty, 17: medical, ...
        # 20: dadrel, 21: relation1, 22: contact1, 23: hphone1, 24: wphone1, 25: cell1,
        # 31: relation2, 32: contact2, 33: hphone2, ...
        # 41: emrelation, 42: emname, 43: emhphone, 44: emwphone, 45: emcell,
        # 46: doctor, 47: docphone, ...
        # 74: email, ...

        student_count = 0
        for row in student_data:
            try:
                studnum = self.safe_get(row, 8)
                if not studnum or studnum == "NULL" or not str(studnum).strip():
                    continue

                lastname = self.safe_get(row, 1)
                firstname = self.safe_get(row, 2)

                if not lastname and not firstname:
                    continue

                # Clean values - remove quotes
                studnum = str(studnum).strip().strip("'")
                lastname = str(lastname).strip().strip("'")
                firstname = str(firstname).strip().strip("'")

                # Create User account
                email_raw = self.safe_get(row, 74)
                if email_raw and email_raw != "NULL" and "@" in str(email_raw):
                    email = str(email_raw).strip().strip("'")
                else:
                    email = f"student{studnum}@school.edu"

                user = User.objects.create(
                    email=email[:254],
                    first_name=firstname[:150],
                    last_name=lastname[:150],
                    password=make_password(STUDENT_PASSWORD),
                    is_staff=False,
                    is_active=True,
                )

                # Create UserRole
                UserRole.objects.create(user=user, school=self.school, role="student")

                # Get form, homeroom, house - clean the values
                grade = self.safe_get(row, 9)
                if grade and grade != "NULL":
                    grade = str(grade).strip().strip("'")
                homeroom_name = self.safe_get(row, 10)
                if homeroom_name and homeroom_name != "NULL":
                    homeroom_name = str(homeroom_name).strip().strip("'")
                house_name = self.safe_get(row, 13)
                if house_name and house_name != "NULL":
                    house_name = str(house_name).strip().strip("'")

                form = self.form_map.get(grade) if grade else None
                homeroom = self.homeroom_map.get(homeroom_name) if homeroom_name else None
                house = self.house_map.get(house_name) if house_name else None

                # Get gender
                sex = self.safe_get(row, 11)
                if sex and str(sex).strip().strip("'") == "M":
                    gender = "M"
                elif sex and str(sex).strip().strip("'") == "F":
                    gender = "F"
                else:
                    gender = "O"

                # Get parent information
                par1_firstname = str(self.safe_get(row, 84, "")).strip().strip("'")
                par1_lastname = str(self.safe_get(row, 85, "")).strip().strip("'")
                par2_firstname = str(self.safe_get(row, 86, "")).strip().strip("'")
                par2_lastname = str(self.safe_get(row, 87, "")).strip().strip("'")

                mother_name = ""
                father_name = ""

                # Determine parent roles based on relation fields
                relation1 = str(self.safe_get(row, 21, "")).strip().strip("'")
                relation2 = str(self.safe_get(row, 31, "")).strip().strip("'")

                if "Mother" in relation1:
                    mother_name = f"{par1_firstname} {par1_lastname}".strip()
                elif "Father" in relation1:
                    father_name = f"{par1_firstname} {par1_lastname}".strip()

                if "Mother" in relation2:
                    mother_name = f"{par2_firstname} {par2_lastname}".strip()
                elif "Father" in relation2:
                    father_name = f"{par2_firstname} {par2_lastname}".strip()

                # If no mother/father detected, use generic parent names
                if not mother_name and par1_firstname:
                    if not father_name:
                        mother_name = f"{par1_firstname} {par1_lastname}".strip()
                    else:
                        mother_name = f"{par1_firstname} {par1_lastname}".strip()

                if not father_name and par2_firstname:
                    father_name = f"{par2_firstname} {par2_lastname}".strip()

                # Get previous school and admission info
                previous_school = str(self.safe_get(row, 61, "")).strip().strip("'")
                admission_year = str(self.safe_get(row, 60, "")).strip().strip("'")

                # Parse admission date
                admission_date = date.today()
                if admission_year and admission_year.isdigit():
                    try:
                        admission_date = date(int(admission_year), 9, 1)
                    except:
                        pass

                # Create Student record
                student = Student.objects.create(
                    school=self.school,
                    user=user,
                    student_id=studnum[:50],
                    first_name=firstname[:100],
                    middle_name=str(self.safe_get(row, 3))[:100].strip().strip("'"),
                    last_name=lastname[:100],
                    form=form,
                    homeroom=homeroom,
                    house=house,
                    gender=gender,
                    date_of_birth=self.parse_date(self.safe_get(row, 12)),
                    phone=str(self.safe_get(row, 25))[:20].strip().strip("'")
                    or str(self.safe_get(row, 23))[:20].strip().strip("'")
                    or str(self.safe_get(row, 33))[:20].strip().strip("'"),
                    email=email[:254],
                    address=str(self.safe_get(row, 27))[:200].strip().strip("'"),
                    city=str(self.safe_get(row, 28))[:100].strip().strip("'"),
                    admission_date=admission_date,
                    previous_school=previous_school[:200],
                    # Parent information
                    mother_name=mother_name[:200],
                    father_name=father_name[:200],
                    # Emergency contact
                    emergency_contact_name=str(self.safe_get(row, 42, ""))[:200].strip().strip("'"),
                    emergency_phone_1=str(self.safe_get(row, 43, ""))[:20].strip().strip("'") or str(self.safe_get(row, 45, ""))[:20].strip().strip("'"),
                    emergency_phone_2=str(self.safe_get(row, 44, ""))[:20].strip().strip("'"),
                    # Doctor
                    doctor_name=str(self.safe_get(row, 46, ""))[:200].strip().strip("'"),
                    doctor_phone=str(self.safe_get(row, 47, ""))[:20].strip().strip("'"),
                )

                self.student_map[studnum] = student
                student_count += 1

                # Create medical record if exists
                medical_info = self.safe_get(row, 17)
                if medical_info and medical_info != "NULL" and len(str(medical_info)) > 3:
                    StudentHealthRecord.objects.create(
                        school=self.school,
                        student=student,
                        category="condition",
                        title="Medical Information",
                        details=str(medical_info)[:1000],
                        severity="medium",
                        is_active=True,
                    )

                # Print progress every 50 students
                if student_count % 50 == 0:
                    print(f"  Processed {student_count} students...")

            except Exception as e:
                print(f"  ⚠ Error migrating student {self.safe_get(row, 8)}: {e}")
                import traceback

                traceback.print_exc()

        print(f"✓ Migrated {student_count} students\n")

    def run_migration(self):
        """Run the complete migration"""
        try:
            print("\n" + "=" * 60)
            print(" SMA TO DJANGO SCHOOL MANAGEMENT SYSTEM MIGRATION")
            print("=" * 60)
            print(f"\nSource: {BACKUP_SQL_FILE}")
            print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

            # Step 1: Clear existing data
            self.clear_existing_data()

            # Step 2: Create school
            with transaction.atomic():
                self.create_school()

            # Step 3: Migrate organizational structures
            with transaction.atomic():
                self.migrate_houses()
                self.migrate_forms_and_homerooms()
                self.migrate_academic_year()

            # Step 4: Migrate staff
            with transaction.atomic():
                self.migrate_staff()

            # Step 5: Migrate students
            with transaction.atomic():
                self.migrate_students()

            # Summary
            print("\n" + "=" * 60)
            print(" MIGRATION COMPLETED SUCCESSFULLY!")
            print("=" * 60)
            print(f"\n📊 SUMMARY:")
            print(f"  • School: {self.school.name}")
            print(f"  • Staff: {len(self.staff_map)}")
            print(f"  • Students: {len(self.student_map)}")
            print(f"  • Forms: {len(self.form_map)}")
            print(f"  • Homerooms: {len(self.homeroom_map)}")
            print(f"  • Houses: {len(self.house_map)}")
            print(f"\n🔐 DEFAULT PASSWORDS:")
            print(f"  • Staff/Admin: {STAFF_PASSWORD}")
            print(f"  • Students: {STUDENT_PASSWORD}")
            print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 60 + "\n")

        except Exception as e:
            print(f"\n❌ MIGRATION FAILED: {e}")
            import traceback

            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    migrator = SMADirectMigrator()
    migrator.run_migration()
