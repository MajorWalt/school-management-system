"""
Django management command to seed the database with sample data.
"""

import random
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from django.db import transaction
from faker import Faker

from core.models import School
from accounts.models import User, UserRole
from staff.models import Staff
from students.models import Student, StudentStatusLog, House
from scheduling.models import Form, Homeroom, AcademicYear, TermConfig, Course, Section, Enrolment, YearPlacement
from attendance.models import Attendance
from grades.models import Evaluation, GradeEntry, GradeWindow
from merits.models import MeritRecord, DemeritRecord

fake = Faker()
Faker.seed(42)
random.seed(42)

DOMINICAN_FIRST_NAMES = [
    "Aaron",
    "Akeem",
    "Alvin",
    "Anthony",
    "Bernard",
    "Brandan",
    "Carlton",
    "Cecilia",
    "Curtis",
    "Damian",
    "Daniel",
    "David",
    "Dennis",
    "Denzel",
    "Dereck",
    "Dominic",
    "Emmanuel",
    "Eric",
    "Everton",
    "Ezekiel",
    "Francine",
    "Frederick",
    "Gideon",
    "Glenroy",
    "Gordon",
    "Gregory",
    "Hayden",
    "Henry",
    "Hilary",
    "Horace",
    "Hugh",
    "Ira",
    "Isaac",
    "Ivan",
    "Jaden",
    "James",
    "Jeffrey",
    "Jeremiah",
    "Jerome",
    "Jerry",
    "Jessica",
    "Jestina",
    "Joel",
    "John",
    "Johnathan",
    "Johnson",
    "Jonathan",
    "Jonathon",
    "Jonas",
    "Joseph",
    "Joshua",
    "Juan",
    "Jude",
    "Judith",
    "Julienne",
    "Julius",
    "Juno",
    "Justin",
]

DOMINICAN_LAST_NAMES = [
    "Albert",
    "Allen",
    "Andrews",
    "Austin",
    "Aymer",
    "Bailey",
    "Baker",
    "Ballantyne",
    "Banfield",
    "Baptiste",
    "Barker",
    "Barnard",
    "Barnett",
    "Baron",
    "Barragan",
    "Barrett",
    "Barry",
    "Barstow",
    "Bartlett",
    "Barton",
    "Basford",
    "Bass",
    "Batchelor",
    "Bates",
    "Bath",
    "Batson",
    "Batts",
    "Bauer",
    "Baughman",
    "Baum",
    "Baumann",
    "Bawden",
    "Baxley",
    "Baxter",
    "Beadle",
    "Beal",
    "Beale",
    "Beall",
    "Beam",
    "Bean",
    "Beard",
    "Bearden",
    "Bearss",
    "Beaulieu",
    "Beavan",
    "Beaver",
    "Beavers",
    "Beca",
    "Bechel",
    "Beck",
    "Becker",
    "Beckett",
    "Beckham",
    "Beckley",
    "Beckman",
]

TEACHERS_FROM_ASC = [
    "Phernicia Hernandez",
    "Sherma Toussaint",
    "Theresa Esteem",
    "John Bailey",
    "David Davis",
    "Michael Garcia",
    "Sarah Wilson",
    "Jennifer Johnson",
    "Robert Brown",
    "Jessica Martinez",
    "James Anderson",
    "Emily Taylor",
    "Daniel Moore",
    "Lisa Jackson",
    "Joseph White",
    "Mary Harris",
    "Christopher Martin",
    "Patricia Lee",
    "Andrew Clark",
    "Barbara Lewis",
    "Kevin Walker",
    "Deborah Hall",
    "Edward Young",
    "Sandra King",
    "Ryan Wright",
    "Dorothy Lopez",
    "Jacob Thompson",
    "Cynthia Hill",
    "Gary Green",
    "Kathleen Adams",
    "Nicholas Nelson",
    "Donna Carter",
    "Isles Shyan",
]

SUBJECTS_FROM_ASC = [
    {"name": "English Language", "code": "Eng"},
    {"name": "French", "code": "Fren"},
    {"name": "Spanish", "code": "Span"},
    {"name": "Mathematics", "code": "Math"},
    {"name": "Integrated Science", "code": "Int-Sci"},
    {"name": "Biology", "code": "Bio"},
    {"name": "Chemistry", "code": "Chem"},
    {"name": "Physics", "code": "Phys"},
    {"name": "Agricultural Science", "code": "Agri"},
    {"name": "Building Technology", "code": "BT"},
    {"name": "Geography", "code": "Geo"},
    {"name": "History", "code": "His"},
    {"name": "Art and Craft", "code": "AC"},
    {"name": "Information Technology", "code": "IT"},
    {"name": "Physical Education", "code": "PE"},
    {"name": "Music", "code": "MU"},
    {"name": "Health and Family Life Education", "code": "HFLE"},
    {"name": "Technical Drawing", "code": "TD"},
    {"name": "Principals of Accounts", "code": "POA"},
    {"name": "Human and Social Biology", "code": "HSB"},
    {"name": "Principals of Business", "code": "POB"},
    {"name": "Literature", "code": "Lit"},
    {"name": "Religion", "code": "Rel"},
]

MERIT_REASONS = [
    "Excellent participation in class",
    "Outstanding performance on assignment",
    "Great teamwork and collaboration",
    "Improved behavior",
    "Exceptional test score",
    "Helping classmates",
    "Good attendance",
    "Leadership shown",
]

DEMERIT_REASONS = [
    "Late to class",
    "Missing homework",
    "Talking in class",
    "Not following instructions",
    "Incomplete assignment",
    "Poor behavior",
    "Absence",
    "Not prepared for class",
]


class Command(BaseCommand):
    help = "Seed the database with sample data for 2024-2025 academic year"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("\n" + "=" * 80))
        self.stdout.write(self.style.SUCCESS("SEEDING EDARA SCHOOL MANAGEMENT SYSTEM (ST. MARY'S ACADEMY)"))
        self.stdout.write(self.style.SUCCESS("=" * 80 + "\n"))

        with transaction.atomic():
            school = self.create_school()
            academic_year = self.create_academic_year(school)
            houses = self.create_houses(school)

            forms = self.create_forms(school)
            homerooms = self.create_homerooms(school, forms)

            teachers, admin_user = self.create_teachers(school)

            students_created = self.create_students(school, forms, homerooms, academic_year, admin_user)

            subjects = self.create_subjects(school)
            sections_dict = self.create_sections_and_enrolments(school, academic_year, forms, subjects)
            self.create_grade_windows(school, academic_year, forms)

            self.create_evaluations_and_grades(school, academic_year, sections_dict, forms)

            self.create_attendance(school, academic_year)

            self.create_merits_and_demerits(school, academic_year)

        self.stdout.write(self.style.SUCCESS("\n" + "=" * 80))
        self.stdout.write(self.style.SUCCESS("SEEDING COMPLETE!"))
        self.stdout.write(self.style.SUCCESS("=" * 80))
        self.stdout.write(self.style.SUCCESS(f"\nSchool: Saint Mary's Academy"))
        self.stdout.write(self.style.SUCCESS(f"Academic Year: 2024-2025"))
        self.stdout.write(self.style.SUCCESS(f"Forms: 5 (Form 1 to Form 5)"))
        self.stdout.write(self.style.SUCCESS(f"Homerooms: 13 (2-3 per form, 10 students each = 130 total)"))
        self.stdout.write(self.style.SUCCESS(f"Teachers: 33 (with user accounts)"))
        self.stdout.write(self.style.SUCCESS(f"Students: 130 (with user accounts)"))
        self.stdout.write(self.style.SUCCESS(f"Subjects: 25 (from aSc export)"))
        self.stdout.write(self.style.SUCCESS(f"Terms: 3"))
        self.stdout.write(self.style.SUCCESS(f"Sections: {5 * 25 * 3} (5 forms × 25 subjects × 3 terms)"))
        self.stdout.write(self.style.SUCCESS(f"\nGrades & Evaluations:"))
        self.stdout.write(self.style.SUCCESS(f"  - Coursework: 20-60 marks"))
        self.stdout.write(self.style.SUCCESS(f"  - Exam: 10-40 marks"))
        self.stdout.write(self.style.SUCCESS(f"  - All students graded in all subjects"))
        self.stdout.write(self.style.SUCCESS(f"\nAttendance:"))
        self.stdout.write(self.style.SUCCESS(f"  - Records for all school days (Mon-Fri)"))
        self.stdout.write(self.style.SUCCESS(f"  - Statuses: present, absent, late, excused"))
        self.stdout.write(self.style.SUCCESS(f"  - Year-scoped with academic_year field"))
        self.stdout.write(self.style.SUCCESS(f"\nMerits & Demerits:"))
        self.stdout.write(self.style.SUCCESS(f"  - Merits: 30% of students (2-5 per student)"))
        self.stdout.write(self.style.SUCCESS(f"  - Demerits: 40% of students (1-3 per student)"))
        self.stdout.write(self.style.SUCCESS(f"\nYearPlacement:"))
        self.stdout.write(self.style.SUCCESS(f"  - Records created for all students (current year)"))
        self.stdout.write(self.style.SUCCESS(f"  - Stores historical form and homeroom per year"))
        self.stdout.write(self.style.SUCCESS(f"\nLogin Credentials:"))
        self.stdout.write(self.style.SUCCESS(f"  Teachers:"))
        self.stdout.write(self.style.SUCCESS(f"    Email: phernandez@smadominica.com | Password: teacher123"))
        self.stdout.write(self.style.SUCCESS(f"    Email: stoussaint@smadominica.com | Password: teacher123"))
        self.stdout.write(self.style.SUCCESS(f"  Students:"))
        self.stdout.write(self.style.SUCCESS(f"    Email: aaron.albert01@student.smadominica.com | Password: student123"))
        self.stdout.write(self.style.SUCCESS(f"    Email: akeem.allen01@student.smadominica.com | Password: student123"))
        self.stdout.write(self.style.SUCCESS(f"  Admin:"))
        self.stdout.write(self.style.SUCCESS(f"    Create via: python manage.py createsuperuser"))
        self.stdout.write(self.style.SUCCESS(f""))

    def create_school(self):
        school, created = School.objects.get_or_create(name="Saint Mary's Academy", defaults={"is_active": True})
        if created:
            self.stdout.write(f"[+] Created school: {school.name}")
        else:
            self.stdout.write(f"[+] Using existing school: {school.name}")
        return school

    def create_academic_year(self, school):
        year, created = AcademicYear.objects.get_or_create(
            school=school,
            name="2024-2025",
            defaults={
                "is_current": True,
                "start_date": datetime(2024, 9, 3).date(),
                "end_date": datetime(2025, 6, 30).date(),
            },
        )
        if created:
            self.stdout.write(f"[+] Created academic year: {year.name}")
        else:
            self.stdout.write(f"[+] Using existing academic year: {year.name}")

        terms = [
            {"term_number": 1, "name": "Term 1", "start": (2024, 9, 3), "end": (2024, 11, 22)},
            {"term_number": 2, "name": "Term 2", "start": (2025, 1, 6), "end": (2025, 3, 28)},
            {"term_number": 3, "name": "Term 3", "start": (2025, 4, 7), "end": (2025, 6, 30)},
        ]

        for term_data in terms:
            TermConfig.objects.get_or_create(
                academic_year=year,
                term_number=term_data["term_number"],
                defaults={
                    "name": term_data["name"],
                    "has_final_exam": True,
                    "coursework_weight": 60,
                    "exam_weight": 40,
                    "start_date": datetime(*term_data["start"]).date(),
                    "end_date": datetime(*term_data["end"]).date(),
                },
            )
        self.stdout.write(f"[+] Created {len(terms)} term configs")
        return year

    def create_teachers(self, school):
        teachers_created = 0
        teachers = {}
        admin_user = None

        for teacher_name in TEACHERS_FROM_ASC:
            cleaned_parts = [p.strip() for p in teacher_name.replace("-", " ").split() if p.strip()]
            if len(cleaned_parts) >= 2:
                first_name = cleaned_parts[0]
                last_name = cleaned_parts[-1]
            else:
                first_name = cleaned_parts[0] if cleaned_parts else "teacher"
                last_name = "staff"
            email = f"{first_name[0].lower()}{last_name.lower()}@smadominica.com"

            user, user_created = User.objects.get_or_create(
                email=email,
                defaults={
                    "first_name": first_name,
                    "last_name": last_name,
                    "password": make_password("teacher123"),
                    "is_active": True,
                },
            )

            # Store first user as admin for YearPlacement recording
            if admin_user is None:
                admin_user = user

            staff, created = Staff.objects.get_or_create(
                school=school,
                user=user,
                defaults={
                    "first_name": first_name,
                    "last_name": last_name,
                    "employee_number": f"EMP{teachers_created:03d}",
                },
            )

            if created:
                teachers_created += 1
                UserRole.objects.get_or_create(
                    user=user,
                    school=school,
                    defaults={"role": "teacher"},
                )
                teachers[teacher_name] = staff

        self.stdout.write(f"[+] Created {teachers_created} teachers with user accounts")
        return teachers, admin_user

    def create_forms(self, school):
        forms = {}
        for form_num in range(1, 6):
            form, created = Form.objects.get_or_create(
                school=school,
                name=f"Form {form_num}",
                defaults={"order": form_num},
            )
            forms[form_num] = form
            if created:
                self.stdout.write(f"[+] Created Form {form_num}")
        return forms

    def create_homerooms(self, school, forms):
        homeroom_mapping = {
            1: ["1A", "1B", "1C"],
            2: ["2A", "2B", "2C"],
            3: ["3A", "3B", "3C"],
            4: ["4A", "4B"],
            5: ["5A", "5B"],
        }

        homerooms = {}
        for form_num, homeroom_names in homeroom_mapping.items():
            form = forms[form_num]
            for homeroom_name in homeroom_names:
                homeroom, created = Homeroom.objects.get_or_create(
                    school=school,
                    form=form,
                    name=homeroom_name,
                    defaults={},
                )
                homerooms[f"Form {form_num} {homeroom_name}"] = homeroom
                if created:
                    self.stdout.write(f"[+] Created Homeroom: Form {form_num} - {homeroom_name}")

        return homerooms

    def create_houses(self, school):
        house_names = ["Garvey", "Marley", "Mandela", "Pan"]
        houses = {}

        for name in house_names:
            house, created = House.objects.get_or_create(
                school=school, name=name, defaults={"color": "#" + "".join([random.choice("0123456789ABCDEF") for _ in range(6)])}
            )
            houses[name] = house
            if created:
                self.stdout.write(f"[+] Created house: {name}")

        return houses

    def create_students(self, school, forms, homerooms, academic_year, recorded_by_user):
        students_created = 0
        accounts_created = 0
        placements_created = 0

        homeroom_list = list(homerooms.values())

        for homeroom in homeroom_list:
            form = homeroom.form

            for i in range(10):
                student_id = f"{homeroom.name}{i + 1:02d}"
                first_name = random.choice(DOMINICAN_FIRST_NAMES)
                last_name = random.choice(DOMINICAN_LAST_NAMES)
                email = f"{first_name.lower()}.{last_name.lower()}{i}@student.smadominica.com"

                # Create or get user account for student
                user, user_created = User.objects.get_or_create(
                    email=email,
                    defaults={
                        "first_name": first_name,
                        "last_name": last_name,
                        "password": make_password("student123"),
                        "is_active": True,
                    },
                )
                if user_created:
                    accounts_created += 1
                    UserRole.objects.get_or_create(
                        user=user,
                        school=school,
                        defaults={"role": "student"},
                    )

                # Create student (user field is optional, leave it null)
                student, created = Student.objects.get_or_create(
                    school=school,
                    student_id=student_id,
                    defaults={
                        "first_name": first_name,
                        "last_name": last_name,
                        "form": form,
                        "homeroom": homeroom,
                        "gender": random.choice(["M", "F"]),
                        "date_of_birth": fake.date_of_birth(minimum_age=10, maximum_age=18),
                        "admission_date": academic_year.start_date,
                        "house": random.choice(list(House.objects.filter(school=school))),
                    },
                )

                if created:
                    students_created += 1
                    StudentStatusLog.objects.get_or_create(
                        student=student,
                        academic_year=academic_year,
                        defaults={
                            "status": "enrolled",
                            "change_date": academic_year.start_date,
                            "reason": "Initial enrolment",
                        },
                    )

                placement, created = YearPlacement.objects.get_or_create(
                    student=student,
                    academic_year=academic_year,
                    defaults={
                        "form": form,
                        "homeroom": homeroom,
                        "outcome": "continuing",
                        "recorded_by": recorded_by_user,
                    },
                )
                if created:
                    placements_created += 1

        self.stdout.write(f"[+] Created {students_created} students")
        self.stdout.write(f"[+] Created {accounts_created} student user accounts")
        self.stdout.write(f"[+] Created {placements_created} YearPlacement records")
        return students_created

    def create_subjects(self, school):
        subjects = {}

        for subject_data in SUBJECTS_FROM_ASC:
            subject, created = Course.objects.get_or_create(
                school=school,
                name=subject_data["name"],
                defaults={
                    "code": subject_data["code"],
                    "short_description": subject_data["code"],
                    "subject_area": "general",
                    "active": True,
                },
            )
            subjects[subject_data["name"]] = subject
            if created:
                self.stdout.write(f"[+] Created subject: {subject_data['name']} ({subject_data['code']})")

        self.stdout.write(f"[+] Created {len(subjects)} subjects from aSc export")
        return subjects

    def create_sections_and_enrolments(self, school, academic_year, forms, subjects):
        students = Student.objects.filter(school=school)
        sections_created = 0
        enrolments_created = 0

        form_students = {}
        for student in students:
            if student.form:
                if student.form not in form_students:
                    form_students[student.form] = []
                form_students[student.form].append(student)

        sections_dict = {}
        for subject in subjects.values():
            for form in forms.values():
                for term_num in [1, 2, 3]:
                    section, created = Section.objects.get_or_create(
                        school=school,
                        course=subject,
                        academic_year=academic_year,
                        term_number=term_num,
                        form=form,
                        defaults={},
                    )
                    if created:
                        sections_created += 1

                    sections_dict[(form, subject, term_num)] = section

                    for student in form_students.get(form, []):
                        enrolment, created = Enrolment.objects.get_or_create(
                            student=student,
                            section=section,
                            defaults={
                                "source": "form",
                            },
                        )
                        if created:
                            enrolments_created += 1

        self.stdout.write(f"[+] Created {sections_created} sections")
        self.stdout.write(f"[+] Created {enrolments_created} enrolments")
        return sections_dict

    def create_grade_windows(self, school, academic_year, forms):
        windows_created = 0

        for form in forms.values():
            for term_num in [1, 2, 3]:
                window, created = GradeWindow.objects.get_or_create(
                    school=school, academic_year=academic_year, term_number=term_num, form=form, defaults={"is_open": True}
                )
                if created:
                    windows_created += 1

        self.stdout.write(f"[+] Created {windows_created} grade windows")

    def create_evaluations_and_grades(self, school, academic_year, sections_dict, forms):
        evaluations_created = 0
        grades_created = 0

        students = Student.objects.filter(school=school)

        for (form, subject, term_num), section in sections_dict.items():
            form_students = students.filter(form=form)

            coursework_eval, created = Evaluation.objects.get_or_create(
                school=school,
                section=section,
                title=f"Coursework - {subject.name}",
                category="coursework",
                subcategory="assignment",
                defaults={
                    "max_marks": 60,
                    "weight": 0.60,
                    "is_final_exam": False,
                    "date": datetime(2024, 9, 15).date() if term_num == 1 else datetime(2025, 1, 15).date() if term_num == 2 else datetime(2025, 4, 15).date(),
                },
            )
            if created:
                evaluations_created += 1

            exam_eval, created = Evaluation.objects.get_or_create(
                school=school,
                section=section,
                title=f"Exam - {subject.name}",
                category="exam",
                subcategory="final_exam",
                defaults={
                    "max_marks": 40,
                    "weight": 0.40,
                    "is_final_exam": True,
                    "date": datetime(2024, 11, 20).date() if term_num == 1 else datetime(2025, 3, 25).date() if term_num == 2 else datetime(2025, 6, 20).date(),
                },
            )
            if created:
                evaluations_created += 1

            for student in form_students:
                enrolment = Enrolment.objects.filter(student=student, section=section).first()
                if not enrolment:
                    continue

                coursework_score = random.randint(20, 60)
                cw_grade, created = GradeEntry.objects.get_or_create(
                    school=school,
                    evaluation=coursework_eval,
                    student=student,
                    defaults={
                        "marks_earned": coursework_score,
                        "is_absent": False,
                    },
                )
                if created:
                    grades_created += 1

                exam_score = random.randint(10, 40)
                exam_grade, created = GradeEntry.objects.get_or_create(
                    school=school,
                    evaluation=exam_eval,
                    student=student,
                    defaults={
                        "marks_earned": exam_score,
                        "is_absent": False,
                    },
                )
                if created:
                    grades_created += 1

        self.stdout.write(f"[+] Created {evaluations_created} evaluations")
        self.stdout.write(f"[+] Created {grades_created} grade entries")

    def create_attendance(self, school, academic_year):
        """Create attendance records for first month only (optimized)."""
        students = list(Student.objects.filter(school=school))
        start_date = academic_year.start_date
        end_date = start_date + timedelta(days=30)  # Only first month

        attendance_created = 0
        current = start_date

        while current <= end_date:
            if current.weekday() < 5:  # Monday to Friday
                for student in students:
                    placement = YearPlacement.objects.filter(student=student, academic_year=academic_year).first()
                    homeroom = placement.homeroom if placement else student.homeroom

                    attendance, created = Attendance.objects.get_or_create(
                        student=student,
                        academic_year=academic_year,
                        date=current,
                        defaults={
                            "school": school,
                            "homeroom": homeroom,
                            "status": random.choice(["present", "absent", "late", "excused"]),
                        },
                    )
                    if created:
                        attendance_created += 1

            current += timedelta(days=1)

        self.stdout.write(f"[+] Created {attendance_created} attendance records (first month)")

    def create_merits_and_demerits(self, school, academic_year):
        students = list(Student.objects.filter(school=school))
        teachers = list(Staff.objects.filter(school=school))
        start_date = academic_year.start_date
        end_date = min(academic_year.end_date, start_date + timedelta(days=60))  # Only 2 months

        merits_created = 0
        demerits_created = 0

        for student in students:
            if random.random() < 0.30:
                num_merits = random.randint(2, 5)
                for _ in range(num_merits):
                    merit_date = start_date + timedelta(days=random.randint(0, (end_date - start_date).days))
                    merit, created = MeritRecord.objects.get_or_create(
                        student=student,
                        date=merit_date,
                        defaults={
                            "school": school,
                            "academic_year": academic_year,
                            "reason": random.choice(MERIT_REASONS),
                            "awarded_by": random.choice(teachers),
                        },
                    )
                    if created:
                        merits_created += 1

        for student in students:
            if random.random() < 0.40:
                num_demerits = random.randint(1, 3)
                for _ in range(num_demerits):
                    demerit_date = start_date + timedelta(days=random.randint(0, (end_date - start_date).days))
                    demerit, created = DemeritRecord.objects.get_or_create(
                        student=student,
                        date=demerit_date,
                        defaults={
                            "school": school,
                            "academic_year": academic_year,
                            "reason": random.choice(DEMERIT_REASONS),
                            "awarded_by": random.choice(teachers),
                        },
                    )
                    if created:
                        demerits_created += 1

        self.stdout.write(f"[+] Created {merits_created} merit records (2 months)")
        self.stdout.write(f"[+] Created {demerits_created} demerit records (2 months)")
