"""
Seed script for Edara school management system (Dominica).

Specifications:
- 1 school (Saint Mary's Academy)
- 1 academic year (2024-2025)
- 2 forms (Form 1, Form 2)
- Form 1: 3 homerooms (101, 102, 103)
- Form 2: 3 homerooms (104, 105, 201)
- 10 students per homeroom
- Auto-generated: courses, sections, enrolments, grades, attendance, etc.

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
from scheduling.models import Form, Homeroom, AcademicYear, TermConfig, Course, Section, Enrolment, TimetablePeriod
from attendance.models import Attendance
from grades.models import Evaluation, GradeEntry, GradeWindow

fake = Faker()
Faker.seed(42)
random.seed(42)

# ── Dominica names ────────────────────────────────────────────────────────────
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
    "Charles",
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

    # Create term configs
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


def create_forms_and_homerooms(school):
    """Create 2 forms with homerooms."""
    forms_data = [
        {"name": "Form 1", "order": 1, "homerooms": [101, 102, 103]},
        {"name": "Form 2", "order": 2, "homerooms": [104, 105, 201]},
    ]

    forms = {}
    homerooms = {}

    for form_data in forms_data:
        form, created = Form.objects.get_or_create(school=school, name=form_data["name"], defaults={"order": form_data["order"]})
        forms[form_data["name"]] = form

        if created:
            print(f"[+] Created {form.name}")

        # Create homerooms
        for hr_num in form_data["homerooms"]:
            homeroom, created = Homeroom.objects.get_or_create(
                school=school,
                form=form,
                name=str(hr_num),
            )
            homerooms[hr_num] = homeroom
            if created:
                print(f"  [+] Created Homeroom {form.name} - {homeroom.name}")

    return forms, homerooms


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


def create_students(school, forms, homerooms):
    """Create 10 students per homeroom."""
    homeroom_list = [101, 102, 103, 104, 105, 201]
    students_created = 0

    for hr_num in homeroom_list:
        homeroom = homerooms[hr_num]
        form = homeroom.form

        for i in range(10):
            student_id = f"{hr_num}{i + 1:02d}"
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
                # Create initial status log
                StudentStatusLog.objects.get_or_create(
                    student=student,
                    defaults={
                        "status": "enrolled",
                        "change_date": datetime(2024, 9, 3).date(),
                        "reason": "Initial enrolment",
                    },
                )

    print(f"[+] Created {students_created} students")
    return students_created


def create_courses(school, forms):
    """Create courses for each form."""
    courses_data = [
        {"name": "English Language", "code": "ENG101", "area": "languages"},
        {"name": "Mathematics", "code": "MAT101", "area": "mathematics"},
        {"name": "Science", "code": "SCI101", "area": "sciences"},
        {"name": "Social Studies", "code": "SOC101", "area": "social_studies"},
        {"name": "Physical Education", "code": "PE101", "area": "physical_ed"},
        {"name": "Information Technology", "code": "IT101", "area": "technology"},
    ]

    courses = {}
    for form in forms.values():
        for course_data in courses_data:
            course, created = Course.objects.get_or_create(
                school=school,
                name=f"{course_data['name']} - {form.name}",
                defaults={
                    "code": f"{course_data['code']}{form.order}",
                    "short_description": course_data["code"],
                    "form": form,
                    "subject_area": course_data["area"],
                    "active": True,
                },
            )
            courses[(form.name, course_data["name"])] = course
            if created:
                print(f"[+] Created course: {course.name}")

    return courses


def create_sections_and_enrolments(school, academic_year, courses, homerooms):
    """Create sections for each course and enrol students."""
    students = Student.objects.filter(school=school)
    sections_created = 0
    enrolments_created = 0

    # Group students by homeroom
    homeroom_students = {}
    for student in students:
        if student.homeroom:
            if student.homeroom not in homeroom_students:
                homeroom_students[student.homeroom] = []
            homeroom_students[student.homeroom].append(student)

    # Create sections and enroll students
    for (form_name, course_name), course in courses.items():
        for term_num in [1, 2, 3]:
            section, created = Section.objects.get_or_create(
                school=school, course=course, academic_year=academic_year, term_number=term_num, form=course.form, defaults={}
            )
            if created:
                sections_created += 1

            # Enroll students from same form
            for homeroom in homerooms.values():
                if homeroom.form == course.form:
                    for student in homeroom_students.get(homeroom, []):
                        enrolment, created = Enrolment.objects.get_or_create(
                            student=student,
                            section=section,
                            defaults={
                                "source": "homeroom",
                                "source_homeroom": homeroom,
                            },
                        )
                        if created:
                            enrolments_created += 1

    print(f"[+] Created {sections_created} sections")
    print(f"[+] Created {enrolments_created} enrolments")


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


def create_attendance(school):
    """Create sample attendance records."""
    students = Student.objects.filter(school=school)[:50]  # Sample for performance
    start_date = datetime(2024, 9, 3).date()
    end_date = datetime(2024, 11, 22).date()

    attendance_created = 0
    current = start_date

    while current <= end_date:
        # Skip weekends
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


def main():
    """Run the seeding process."""
    print("\n" + "=" * 60)
    print("SEEDING EDARA SCHOOL MANAGEMENT SYSTEM")
    print("=" * 60 + "\n")

    with transaction.atomic():
        # Create base entities
        school = create_school()
        year = create_academic_year(school)
        houses = create_houses(school)
        forms, homerooms = create_forms_and_homerooms(school)

        # Create students
        create_students(school, forms, homerooms)

        # Create academic content
        courses = create_courses(school, forms)
        create_sections_and_enrolments(school, year, courses, homerooms)
        create_grade_windows(school, year, forms)

        # Create attendance
        create_attendance(school)

    print("\n" + "=" * 60)
    print("SEEDING COMPLETE!")
    print("=" * 60)
    print(f"\nLogin credentials:")
    print(f"  Email: wgreenaway@smadominica.com")
    print(f"  Password: greenaway")
    print()


if __name__ == "__main__":
    main()
