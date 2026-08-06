"""
Seed script for Edara school management system (Dominica).

Specifications for 2024-2025:
- 1 school (Saint Mary's Academy)
- 1 academic year (2024-2025)
- 5 forms (Form 1, Form 2, Form 3, Form 4, Form 5)
- 13 homerooms (2-3 per form, 10 students per homeroom = 130 students)
- 33 teachers with user accounts
- 130 students with user accounts
- 25 subjects with sections for each form/term
- Grades for all students across all terms
- Attendance records for all students
- Merits and Demerits for students
- YearPlacement records for year-scoping

Run from project root:
    python manage.py shell < seed_data.py
"""

import os
import django
import random
from datetime import datetime, timedelta

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from faker import Faker
from django.contrib.auth.hashers import make_password
from django.db import transaction

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


def create_school():
    """Get or create the school."""
    school, created = School.objects.get_or_create(name="Saint Mary's Academy", defaults={"is_active": True})
    if created:
        print(f"[+] Created school: {school.name}")
    else:
        print(f"[+] Using existing school: {school.name}")
    return school


def create_academic_year(school):
    """Create academic year 2024-2025."""
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
        print(f"[+] Created academic year: {year.name}")
    else:
        print(f"[+] Using existing academic year: {year.name}")

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
    print(f"[+] Created {len(terms)} term configs")
    return year


def generate_teacher_email(full_name):
    """Generate teacher email from full name."""
    cleaned_parts = [p.strip() for p in full_name.replace("-", " ").split() if p.strip()]
    if len(cleaned_parts) >= 2:
        first_name = cleaned_parts[0]
        last_name = cleaned_parts[-1]
    else:
        first_name = cleaned_parts[0] if cleaned_parts else "teacher"
        last_name = "staff"
    email = f"{first_name[0].lower()}{last_name.lower()}@smadominica.com"
    return email


def create_teachers(school):
    """Create 33 teachers with user accounts."""
    teachers_created = 0
    teachers = {}

    for teacher_name in TEACHERS_FROM_ASC:
        email = generate_teacher_email(teacher_name)

        user, user_created = User.objects.get_or_create(
            email=email,
            defaults={
                "first_name": teacher_name.split()[0],
                "last_name": teacher_name.split()[-1],
                "password": make_password("teacher123"),
                "is_active": True,
            },
        )

        name_parts = teacher_name.split()
        first_name = name_parts[0]
        last_name = name_parts[-1] if len(name_parts) > 1 else "Staff"

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

    print(f"[+] Created {teachers_created} teachers with user accounts")
    return teachers


def create_forms(school):
    """Create 5 forms (Form 1 to Form 5)."""
    forms = {}
    for form_num in range(1, 6):
        form, created = Form.objects.get_or_create(
            school=school,
            name=f"Form {form_num}",
            defaults={"order": form_num},
        )
        forms[form_num] = form
        if created:
            print(f"[+] Created Form {form_num}")
    return forms


def create_homerooms(school, forms):
    """Create homerooms for each form (2-3 per form, 10 students each)."""
    homeroom_mapping = {
        1: ["1A", "1B", "1C"],  # Form 1: 3 homerooms
        2: ["2A", "2B", "2C"],  # Form 2: 3 homerooms
        3: ["3A", "3B", "3C"],  # Form 3: 3 homerooms
        4: ["4A", "4B"],  # Form 4: 2 homerooms
        5: ["5A", "5B"],  # Form 5: 2 homerooms
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
                print(f"[+] Created Homeroom: Form {form_num} - {homeroom_name}")

    return homerooms


def create_houses(school):
    """Create 4 houses."""
    house_names = ["Garvey", "Marley", "Mandela", "Pan"]
    houses = {}

    for name in house_names:
        house, created = House.objects.get_or_create(
            school=school, name=name, defaults={"color": "#" + "".join([random.choice("0123456789ABCDEF") for _ in range(6)])}
        )
        houses[name] = house
        if created:
            print(f"[+] Created house: {name}")

    return houses


def create_students(school, forms, homerooms, academic_year):
    """Create 10 students per homeroom with user accounts and YearPlacement."""
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

            # Create student account
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

            # Create student
            student, created = Student.objects.get_or_create(
                school=school,
                student_id=student_id,
                defaults={
                    "user": user,
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

            # Create YearPlacement record
            placement, created = YearPlacement.objects.get_or_create(
                student=student,
                academic_year=academic_year,
                defaults={
                    "form": form,
                    "homeroom": homeroom,
                    "outcome": "continuing",
                },
            )
            if created:
                placements_created += 1

    print(f"[+] Created {students_created} students")
    print(f"[+] Created {accounts_created} student user accounts")
    print(f"[+] Created {placements_created} YearPlacement records")
    return students_created


def create_subjects(school):
    """Create 25 subjects from aSc export."""
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
            print(f"[+] Created subject: {subject_data['name']} ({subject_data['code']})")

    print(f"[+] Created {len(subjects)} subjects from aSc export")
    return subjects


def create_sections_and_enrolments(school, academic_year, forms, subjects):
    """Create sections for each subject and enrol students."""
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

    print(f"[+] Created {sections_created} sections")
    print(f"[+] Created {enrolments_created} enrolments")
    return sections_dict


def create_grade_windows(school, academic_year, forms):
    """Create grade entry windows for each form/term."""
    windows_created = 0

    for form in forms.values():
        for term_num in [1, 2, 3]:
            window, created = GradeWindow.objects.get_or_create(
                school=school, academic_year=academic_year, term_number=term_num, form=form, defaults={"is_open": True}
            )
            if created:
                windows_created += 1

    print(f"[+] Created {windows_created} grade windows")


def create_evaluations_and_grades(school, academic_year, sections_dict, forms):
    """Create evaluations and grade entries for all students."""
    evaluations_created = 0
    grades_created = 0

    students = Student.objects.filter(school=school)

    for (form, subject, term_num), section in sections_dict.items():
        form_students = students.filter(form=form)

        # Create coursework evaluation
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

        # Create exam evaluation
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

        # Create grade entries for each student
        for student in form_students:
            enrolment = Enrolment.objects.filter(student=student, section=section).first()
            if not enrolment:
                continue

            # Coursework grade
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

            # Exam grade
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

    print(f"[+] Created {evaluations_created} evaluations")
    print(f"[+] Created {grades_created} grade entries")


def create_attendance(school, academic_year):
    """Create attendance records for all students."""
    students = Student.objects.filter(school=school)
    start_date = academic_year.start_date
    end_date = academic_year.end_date

    attendance_created = 0
    current = start_date

    while current <= end_date:
        if current.weekday() < 5:  # Monday to Friday
            for student in students:
                # Get homeroom for this year
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

    print(f"[+] Created {attendance_created} attendance records")


def create_merits_and_demerits(school, academic_year):
    """Create merit and demerit records for students."""
    students = Student.objects.filter(school=school)
    teachers = Staff.objects.filter(school=school)
    start_date = academic_year.start_date
    end_date = academic_year.end_date

    merits_created = 0
    demerits_created = 0

    # Create merits for students
    for student in students:
        # 30% of students get 2-5 merits
        if random.random() < 0.30:
            num_merits = random.randint(2, 5)
            for _ in range(num_merits):
                merit_date = start_date + timedelta(days=random.randint(0, (end_date - start_date).days))
                merit, created = MeritRecord.objects.get_or_create(
                    student=student,
                    date=merit_date,
                    count=random.randint(1, 3),
                    defaults={
                        "school": school,
                        "academic_year": academic_year,
                        "reason": random.choice(MERIT_REASONS),
                        "awarded_by": random.choice(teachers),
                    },
                )
                if created:
                    merits_created += 1

    # Create demerits for students
    for student in students:
        # 40% of students get 1-3 demerits
        if random.random() < 0.40:
            num_demerits = random.randint(1, 3)
            for _ in range(num_demerits):
                demerit_date = start_date + timedelta(days=random.randint(0, (end_date - start_date).days))
                demerit, created = DemeritRecord.objects.get_or_create(
                    student=student,
                    date=demerit_date,
                    count=random.randint(1, 2),
                    defaults={
                        "school": school,
                        "academic_year": academic_year,
                        "reason": random.choice(DEMERIT_REASONS),
                        "awarded_by": random.choice(teachers),
                    },
                )
                if created:
                    demerits_created += 1

    print(f"[+] Created {merits_created} merit records")
    print(f"[+] Created {demerits_created} demerit records")


def main():
    """Run the seeding process."""
    print("\n" + "=" * 80)
    print("SEEDING EDARA SCHOOL MANAGEMENT SYSTEM (ST. MARY'S ACADEMY)")
    print("=" * 80 + "\n")

    with transaction.atomic():
        school = create_school()
        academic_year = create_academic_year(school)
        houses = create_houses(school)

        forms = create_forms(school)
        homerooms = create_homerooms(school, forms)

        teachers = create_teachers(school)

        students_created = create_students(school, forms, homerooms, academic_year)

        subjects = create_subjects(school)
        sections_dict = create_sections_and_enrolments(school, academic_year, forms, subjects)
        create_grade_windows(school, academic_year, forms)

        create_evaluations_and_grades(school, academic_year, sections_dict, forms)

        create_attendance(school, academic_year)

        create_merits_and_demerits(school, academic_year)

    print("\n" + "=" * 80)
    print("SEEDING COMPLETE!")
    print("=" * 80)
    print(f"\nSchool: Saint Mary's Academy")
    print(f"Academic Year: 2024-2025")
    print(f"Forms: 5 (Form 1 to Form 5)")
    print(f"Homerooms: 13 (2-3 per form, 10 students each = 130 total)")
    print(f"Teachers: 33 (with user accounts)")
    print(f"Students: 130 (with user accounts)")
    print(f"Subjects: 25 (from aSc export)")
    print(f"Terms: 3")
    print(f"Sections: {5 * 25 * 3} (5 forms × 25 subjects × 3 terms)")
    print(f"\nGrades & Evaluations:")
    print(f"  - Coursework: 20-60 marks")
    print(f"  - Exam: 10-40 marks")
    print(f"  - All students graded in all subjects")
    print(f"\nAttendance:")
    print(f"  - Records for all school days (Mon-Fri)")
    print(f"  - Statuses: present, absent, late, excused")
    print(f"  - Year-scoped with academic_year field")
    print(f"\nMerits & Demerits:")
    print(f"  - Merits: 30% of students (2-5 per student)")
    print(f"  - Demerits: 40% of students (1-3 per student)")
    print(f"\nYearPlacement:")
    print(f"  - Records created for all students (current year)")
    print(f"  - Stores historical form and homeroom per year")
    print(f"\nLogin Credentials:")
    print(f"  Teachers:")
    print(f"    Email: phernandez@smadominica.com | Password: teacher123")
    print(f"    Email: stoussaint@smadominica.com | Password: teacher123")
    print(f"  Students:")
    print(f"    Email: aaron.albert01@student.smadominica.com | Password: student123")
    print(f"    Email: akeem.allen01@student.smadominica.com | Password: student123")
    print(f"  Admin:")
    print(f"    Create via: python manage.py createsuperuser")
    print()


if __name__ == "__main__":
    main()
