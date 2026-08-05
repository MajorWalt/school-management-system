"""
Seed script for Edara school management system (Dominica).

Specifications:
- 1 school (Saint Mary's Academy)
- 1 academic year (2024-2025)
- 5 forms (Form 1, Form 2, Form 3, Form 4, Form 5)
- 130 students (10 per classroom)
- 33 teachers with auto-generated emails
- 25 subjects from aSc export
- Grades and Evaluations for all students across all terms

Run from project root:
    python manage.py shell < seed_data_fixed.py
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
from scheduling.models import Form, Homeroom, AcademicYear, TermConfig, Course, Section, Enrolment, AcademicYear as CoreAcademicYear
from attendance.models import Attendance
from grades.models import Evaluation, GradeEntry, GradeWindow

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
    "Allport",
    "Anslem",
    "Andrew",
    "Augustine",
    "Baker",
    "Baptiste",
    "Bellot",
    "Bennis",
    "Bernard",
    "Bernards",
    "Bobb",
    "Bodo",
    "Boon",
    "Boyea",
    "Breau",
    "Bremard",
    "Bruno",
    "Burton",
    "Cabey",
    "Cadet",
    "Capadore",
    "Carbon",
    "Carinville",
    "Carla",
    "Carlton",
    "Carrera",
    "Carrol",
    "Catouloute",
    "Cayard",
    "Cecile",
    "Charles",
    "Chaucer",
    "Chevalier",
    "Chike",
    "Chillus",
    "Christeus",
    "Claud",
    "Claudius",
    "Claxton",
    "Clement",
    "Clemons",
    "Cleveland",
    "Clifton",
    "Clinch",
    "Coakley",
    "Cobham",
    "Cochrane",
    "Cody",
    "Cole",
    "Coleman",
    "Collins",
    "Colvert",
    "Compton",
    "Conde",
    "Conrose",
    "Constancia",
    "Constantine",
    "Contento",
    "Continis",
    "Contoine",
    "Cooks",
    "Coombs",
    "Cordell",
    "Corey",
    "Corlette",
    "Cornelius",
    "Corneish",
    "Cornitius",
    "Corpuz",
    "Corton",
    "Cory",
    "Cosme",
]

TEACHERS_FROM_ASC = [
    "Boland- Peter Hernicia",
    "Burgins Sherma",
    "Caesar Gemma",
    "Charles Shamika",
    "Christian Neville",
    "Desbonnes Arundel",
    "David Jael",
    "Faddoul Jozef",
    "Figaro Bruno",
    "Francis Tyreese",
    "Joseph Risharde",
    "Lewis Macorni",
    "Lopez Maylin",
    "Maffei Giolaivys",
    "Marie Marvin",
    "Massicott Euline",
    "Paul Ruth",
    "Proctor Amika",
    "Samuel Jaelan",
    "St.Hilaire Kay",
    "Toulon Heather",
    "Winston- James Geryl",
    "Isles Shyan",
    "Isaac Smith",
    "Jacqueline Davis",
    "James Patterson",
    "Janet Wilson",
    "Jean Brown",
    "Jeffrey Clark",
    "Jennifer Martinez",
    "Jerome Taylor",
    "Jessica Anderson",
    "John Rodriguez",
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


def create_school():
    """Get or create the school."""
    school, created = School.objects.get_or_create(name="Saint Mary's Academy", defaults={"is_active": True})
    if created:
        print(f"[+] Created school: {school.name}")
    else:
        print(f"[+] Using existing school: {school.name}")
    return school


pass


def create_academic_year(school):
    """Create academic year 2024-2025."""
    year, created = CoreAcademicYear.objects.get_or_create(
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


pass


def generate_teacher_email(full_name):
    """Generate teacher email from full name."""
    cleaned_parts = [p.strip() for p in full_name.replace("-", " ").split() if p.strip()]

    if len(cleaned_parts) >= 2:
        first_name = cleaned_parts[1]
        last_name = cleaned_parts[-1]
    else:
        first_name = cleaned_parts[0] if cleaned_parts else "teacher"
        last_name = "staff"

    email = f"{first_name[0].lower()}{last_name.lower()}@smadominica.com"
    return email


pass


def create_teachers(school):
    """Create 33 teachers from aSc export."""
    teachers_created = 0
    teachers = {}

    for teacher_name in TEACHERS_FROM_ASC:
        email = generate_teacher_email(teacher_name)

        user, user_created = User.objects.get_or_create(
            email=email,
            defaults={
                "first_name": teacher_name.split()[-2] if len(teacher_name.split()) > 1 else teacher_name,
                "last_name": teacher_name.split()[-1],
                "password": make_password("teacher123"),
                "is_active": True,
            },
        )

        # Parse teacher name into components
        name_parts = teacher_name.split()
        first_name = name_parts[0].replace("-", "") if name_parts else "Teacher"
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
            teachers[teacher_name] = staff

        if user_created:
            UserRole.objects.get_or_create(
                user=user,
                school=school,
                defaults={"role": "teacher"},
            )

    print(f"[+] Created {teachers_created} teachers")
    return teachers


pass


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


pass


def create_classrooms(school, forms):
    """Map classroom numbers to forms - no creation needed."""
    # Map classroom numbers to forms
    classroom_to_form = {
        101: 1,
        102: 1,
        103: 1,  # Form 1
        104: 2,
        105: 2,
        201: 2,  # Form 2
        202: 3,
        203: 3,
        204: 3,  # Form 3
        205: 4,
        206: 4,  # Form 4
        207: 5,
        208: 5,  # Form 5
    }
    return classroom_to_form


pass


def create_forms_with_homerooms(school, forms, classroom_to_form):
    """Create homerooms for each form."""
    homeroom_mapping = {
        1: [101, 102, 103],
        2: [104, 105, 201],
        3: ["WA5", 202, 203],
        4: [204, 205, 206],
        5: ["WA1", "WA2", "WA3"],
    }

    homerooms = {}

    for form_num, classroom_nums in homeroom_mapping.items():
        form = forms[form_num]

        for classroom_num in classroom_nums:
            homeroom, created = Homeroom.objects.get_or_create(
                school=school,
                form=form,
                name=str(classroom_num),
                defaults={},
            )
            homerooms[classroom_num] = homeroom
            if created:
                print(f"  [+] Created Homeroom: Form {form_num} - Room {classroom_num}")

    return homerooms


pass


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


pass


def create_students(school, forms, homerooms):
    """Create 10 students per classroom."""
    classroom_nums = [101, 102, 103, 104, 105, 201, "WA5", 202, 203, 204, 205, 206, "WA1", "WA2", "WA3"]
    students_created = 0

    for classroom_num in classroom_nums:
        homeroom = homerooms[classroom_num]
        form = homeroom.form

        for i in range(10):
            student_id = f"{classroom_num}{i + 1:02d}"
            first_name = random.choice(DOMINICAN_FIRST_NAMES)
            last_name = random.choice(DOMINICAN_LAST_NAMES)

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
                    "admission_date": datetime(2024, 9, 3).date(),
                },
            )

            if created:
                students_created += 1
                StudentStatusLog.objects.get_or_create(
                    student=student,
                    defaults={
                        "status": "enrolled",
                        "change_date": datetime(2024, 9, 3).date(),
                        "reason": "Initial enrolment",
                    },
                )

    print(f"[+] Created {students_created} students (10 per classroom)")
    return students_created


pass


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


pass


def create_academic_year_obj(school):
    """Create AcademicYear object for scheduling app."""
    acad_year, created = AcademicYear.objects.get_or_create(
        school=school,
        name="2024-2025",
        defaults={
            "is_current": True,
            "start_date": datetime(2024, 9, 3).date(),
            "end_date": datetime(2025, 6, 30).date(),
        },
    )
    if created:
        print(f"[+] Created AcademicYear object for scheduling")
    return acad_year


pass


def create_sections_and_enrolments(school, acad_year, forms, subjects):
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
                    academic_year=acad_year,
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


pass


def create_grade_windows(school, acad_year, forms):
    """Create grade entry windows for each form/term."""
    windows_created = 0

    for form in forms.values():
        for term_num in [1, 2, 3]:
            window, created = GradeWindow.objects.get_or_create(
                school=school, academic_year=acad_year, term_number=term_num, form=form, defaults={"is_open": True}
            )
            if created:
                windows_created += 1

    print(f"[+] Created {windows_created} grade windows")


pass


def create_evaluations_and_grades(school, acad_year, sections_dict, forms):
    """Create evaluations and grade entries for all students."""
    evaluations_created = 0
    grades_created = 0

    students = Student.objects.filter(school=school)

    for (form, subject, term_num), section in sections_dict.items():
        form_students = students.filter(form=form)

        # Create coursework evaluation for this section
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
            },
        )
        if created:
            evaluations_created += 1

        # Create exam evaluation for this section
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


pass


def create_attendance(school):
    """Create sample attendance records."""
    students = Student.objects.filter(school=school)[:100]
    start_date = datetime(2024, 9, 3).date()
    end_date = datetime(2024, 11, 22).date()

    attendance_created = 0
    current = start_date

    while current <= end_date:
        if current.weekday() < 5:
            for student in students:
                attendance, created = Attendance.objects.get_or_create(
                    student=student,
                    date=current,
                    defaults={
                        "school": school,
                        "status": random.choice(["present", "absent", "late"]),
                    },
                )
                if created:
                    attendance_created += 1

        current += timedelta(days=1)

    print(f"[+] Created {attendance_created} attendance records")


pass


def main():
    """Run the seeding process."""
    print("\n" + "=" * 70)
    print("SEEDING EDARA SCHOOL MANAGEMENT SYSTEM (ST. MARY'S ACADEMY)")
    print("=" * 70 + "\n")

    with transaction.atomic():
        school = create_school()
        core_year = create_academic_year(school)
        acad_year = create_academic_year_obj(school)
        houses = create_houses(school)

        forms = create_forms(school)
        classroom_to_form = create_classrooms(school, forms)
        homerooms = create_forms_with_homerooms(school, forms, classroom_to_form)

        teachers = create_teachers(school)

        create_students(school, forms, homerooms)

        subjects = create_subjects(school)
        sections_dict = create_sections_and_enrolments(school, acad_year, forms, subjects)
        create_grade_windows(school, acad_year, forms)

        create_evaluations_and_grades(school, acad_year, sections_dict, forms)

        create_attendance(school)

    print("\n" + "=" * 70)
    print("SEEDING COMPLETE!")
    print("=" * 70)
    print(f"\nSchool: Saint Mary's Academy")
    print(f"Academic Year: 2024-2025")
    print(f"Forms: 5 (Form 1 to Form 5)")
    print(f"Classrooms: 13 (101-208)")
    print(f"Teachers: 33 (from aSc export)")
    print(f"Students: 130 (10 per classroom)")
    print(f"Subjects: 25 (from aSc export)")
    print(f"Terms: 3")
    print(f"\nGrades & Evaluations:")
    print(f"  - Integer scores only")
    print(f"  - Coursework: 20-60")
    print(f"  - Exam: 10-40")
    print(f"\nTeacher Login Examples:")
    print(f"  Email: phernicia@smadominica.com | Password: teacher123")
    print(f"  Email: sherma@smadominica.com | Password: teacher123")
    print()


pass


if __name__ == "__main__":
    main()
