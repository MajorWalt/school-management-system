"""
Seed script for Edara school management system.
Creates:
  - Academic Year (2024-2025) with 3 Term Configs
  - Form 1 with homerooms 101, 102, 103
  - 8 Teachers (Staff + User + UserRole)
  - 84 Students all male (28 per homeroom) with User + UserRole + StatusLog
  - 8 Courses
  - Sections linking courses to Form 1 for each term
  - Enrolments for all students in all sections
  - Sample attendance, grade entries, merits/demerits

Run from project root:
    python manage.py shell < seed_data.py
"""

import os
import django
import random
import datetime

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth.hashers import make_password
from core.models import School
from accounts.models import User, UserRole
from staff.models import Staff
from students.models import Student, StudentStatusLog
from scheduling.models import (
    Form, Homeroom, AcademicYear, TermConfig, Course, Section, Enrolment
)
from attendance.models import Attendance
from grades.models import GradeEntry
from merits.models import MeritRecord, DemeritRecord

print("🌱 Starting seed...")

# ── Get existing school ───────────────────────────────────────────────────────

school = School.objects.filter(is_active=True).first()
if not school:
    print("❌ No active school found. Create one in the admin first.")
    exit()

print(f"  Using school: {school.name} (slug: {school.slug})")

# ── Helpers ───────────────────────────────────────────────────────────────────

FIRST_NAMES_M = [
    "James", "John", "Robert", "Michael", "William", "David", "Richard",
    "Joseph", "Thomas", "Charles", "Christopher", "Daniel", "Matthew",
    "Anthony", "Mark", "Donald", "Steven", "Paul", "Andrew", "Joshua",
    "Kevin", "Brian", "George", "Edward", "Ronald", "Timothy", "Jason",
    "Jeffrey", "Ryan", "Jacob", "Nathan", "Tyler", "Aaron", "Adam",
    "Zachary", "Eric", "Nicholas", "Jonathan", "Stephen", "Patrick",
    "Sean", "Justin", "Benjamin", "Samuel", "Raymond", "Gregory",
    "Frank", "Alexander", "Harold", "Dennis",
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez",
    "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
    "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark",
    "Ramirez", "Lewis", "Robinson", "Walker", "Young", "Allen", "King",
    "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores", "Green",
    "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell",
    "Carter", "Phillips",
]

MERIT_CATEGORIES   = ["academic", "behaviour", "sports", "arts", "community", "leadership"]
DEMERIT_CATEGORIES = ["misconduct", "tardiness", "uniform", "disrespect", "other"]

MERIT_REASONS = [
    "Outstanding performance in class test",
    "Excellent participation in group work",
    "Representing school in competition",
    "Community service contribution",
    "Consistent homework submission",
    "Leadership shown during school event",
]

DEMERIT_REASONS = [
    "Arrived late to class",
    "Incomplete uniform",
    "Disruptive behaviour in class",
    "Incomplete homework",
    "Disrespectful to teacher",
]

used_emails = set(User.objects.values_list("email", flat=True))

def unique_email(first, last, suffix=""):
    base  = f"{first.lower()}.{last.lower()}{suffix}"
    email = f"{base}@school.edu"
    count = 1
    while email in used_emails:
        email = f"{base}{count}@school.edu"
        count += 1
    used_emails.add(email)
    return email

def random_dob():
    start = datetime.date(2009, 1, 1)
    end   = datetime.date(2012, 12, 31)
    delta = (end - start).days
    return start + datetime.timedelta(days=random.randint(0, delta))

def random_date_this_year():
    today = datetime.date.today()
    start = datetime.date(today.year, 1, 15)
    delta = (today - start).days
    if delta <= 0:
        return start
    return start + datetime.timedelta(days=random.randint(0, delta))


# ── 1. Academic Year + Term Configs ───────────────────────────────────────────

year, created = AcademicYear.objects.get_or_create(
    school=school,
    name="2024-2025",
    defaults={"is_current": True}
)
print(f"  {'Created' if created else 'Found'} academic year: {year.name}")

term_data = [
    {"term_number": 1, "name": "Term 1", "has_final_exam": True,  "coursework_weight": 60, "exam_weight": 40},
    {"term_number": 2, "name": "Term 2", "has_final_exam": False, "coursework_weight": 100, "exam_weight": 0},
    {"term_number": 3, "name": "Term 3", "has_final_exam": True,  "coursework_weight": 60, "exam_weight": 40},
]

for td in term_data:
    obj, created = TermConfig.objects.get_or_create(
        academic_year=year,
        term_number=td["term_number"],
        defaults={
            "name":              td["name"],
            "has_final_exam":    td["has_final_exam"],
            "coursework_weight": td["coursework_weight"],
            "exam_weight":       td["exam_weight"],
        }
    )
    print(f"  {'Created' if created else 'Found'} term config: {obj.name}")


# ── 2. Form 1 + Homerooms ─────────────────────────────────────────────────────

form1, created = Form.objects.get_or_create(
    school=school,
    name="Form 1",
    defaults={"order": 1}
)
print(f"  {'Created' if created else 'Found'} form: {form1.name}")

homerooms = {}
for hr_name in ["101", "102", "103"]:
    hr, created = Homeroom.objects.get_or_create(
        school=school,
        name=hr_name,
        defaults={"form": form1}
    )
    homerooms[hr_name] = hr
    print(f"  {'Created' if created else 'Found'} homeroom: {hr.name}")


# ── 3. Courses ────────────────────────────────────────────────────────────────

course_names = [
    ("Mathematics",            "MATH"),
    ("English Language",       "ENG"),
    ("Integrated Science",     "SCI"),
    ("Social Studies",         "SS"),
    ("Physical Education",     "PE"),
    ("Information Technology", "IT"),
    ("Art & Design",           "ART"),
    ("French",                 "FRE"),
]

courses = {}
for name, code in course_names:
    c, _ = Course.objects.get_or_create(
        school=school,
        name=name,
        defaults={"code": code, "active": True}
    )
    courses[code] = c
print(f"  {len(courses)} courses ready.")


# ── 4. Teachers ───────────────────────────────────────────────────────────────

teacher_data = [
    ("Alice",  "Thompson", "F", "Mathematics",       "Mathematics Teacher",     "Mathematics"),
    ("Brian",  "Edwards",  "M", "Languages",         "English Teacher",         "English Language"),
    ("Carol",  "Bennett",  "F", "Sciences",          "Science Teacher",         "Integrated Science"),
    ("David",  "Foster",   "M", "Social Studies",    "History Teacher",         "Social Studies"),
    ("Emma",   "Hughes",   "F", "Physical Education","PE Teacher",              "Physical Education"),
    ("Frank",  "Morris",   "M", "Technology",        "IT Teacher",              "Information Technology"),
    ("Grace",  "Russell",  "F", "Arts",              "Art Teacher",             "Art & Design"),
    ("Henry",  "Coleman",  "M", "Languages",         "French Teacher",          "French"),
]

teachers = []
for i, (first, last, gender, dept, role_title, spec) in enumerate(teacher_data, start=1):
    email = unique_email(first, last, ".staff")

    user, _ = User.objects.get_or_create(
        email=email,
        defaults={
            "first_name": first,
            "last_name":  last,
            "password":   make_password("teacher123"),
            "is_active":  True,
        }
    )
    UserRole.objects.get_or_create(user=user, school=school, role="teacher")

    staff, _ = Staff.objects.get_or_create(
        school=school,
        employee_number=f"T{i:03d}",
        defaults={
            "user":                   user,
            "first_name":             first,
            "last_name":              last,
            "gender":                 gender,
            "email":                  email,
            "department":             dept,
            "role_title":             role_title,
            "subject_specialisation": spec,
            "hire_date":              datetime.date(2020, 9, 1),
            "active":                 True,
        }
    )
    teachers.append(staff)

print(f"  {len(teachers)} teachers ready.")


# ── 5. Sections ───────────────────────────────────────────────────────────────

course_teacher_map = {
    "MATH": 0, "ENG": 1, "SCI": 2, "SS": 3,
    "PE":   4, "IT":  5, "ART": 6, "FRE": 7,
}

sections = {}
for code, course in courses.items():
    teacher_idx = course_teacher_map.get(code, 0)
    teacher     = teachers[teacher_idx]
    for term_num in [1, 2, 3]:
        sec, _ = Section.objects.get_or_create(
            school=school,
            course=course,
            academic_year=year,
            term_number=term_num,
            form=form1,
            defaults={"teacher": teacher, "room": f"Room {random.randint(1, 10)}"}
        )
        sections[(code, term_num)] = sec

print(f"  {len(sections)} sections ready.")


# ── 6. Students (all male) ────────────────────────────────────────────────────

all_students = []
student_counter = 1

for hr_name, homeroom in homerooms.items():
    for i in range(28):
        first = random.choice(FIRST_NAMES_M)
        last  = random.choice(LAST_NAMES)
        email = unique_email(first, last, f".{hr_name}")
        sid   = f"2025{student_counter:04d}"

        user, _ = User.objects.get_or_create(
            email=email,
            defaults={
                "first_name": first,
                "last_name":  last,
                "password":   make_password("student123"),
                "is_active":  True,
            }
        )
        UserRole.objects.get_or_create(user=user, school=school, role="student")

        student, created = Student.objects.get_or_create(
            school=school,
            student_id=sid,
            defaults={
                "user":           user,
                "first_name":     first,
                "last_name":      last,
                "gender":         "M",
                "date_of_birth":  random_dob(),
                "email":          email,
                "form":           form1,
                "homeroom":       homeroom,
                "admission_date": datetime.date(2024, 9, 3),
            }
        )

        if created:
            StudentStatusLog.objects.create(
                student     = student,
                status      = "enrolled",
                change_date = datetime.date(2024, 9, 3),
                reason      = "Initial enrolment",
                changed_by  = user,
            )

        all_students.append(student)
        student_counter += 1

print(f"  {len(all_students)} students ready.")


# ── 7. Enrolments ─────────────────────────────────────────────────────────────

enrolment_count = 0
for student in all_students:
    for (code, term_num), section in sections.items():
        _, created = Enrolment.objects.get_or_create(
            student=student,
            section=section,
        )
        if created:
            enrolment_count += 1

print(f"  {enrolment_count} enrolments created.")


# ── 8. Attendance (last 10 school days) ───────────────────────────────────────

admin_user = User.objects.filter(is_superuser=True).first()
today      = datetime.date.today()

school_days = []
d = today
while len(school_days) < 10:
    if d.weekday() < 5:
        school_days.append(d)
    d -= datetime.timedelta(days=1)

att_count = 0
math_section = sections[("MATH", 1)]

for student in all_students:
    for day in school_days:
        roll = random.random()
        if roll < 0.90:
            status = "present"
        elif roll < 0.97:
            status = "absent"
        else:
            status = "late"

        _, created = Attendance.objects.get_or_create(
            school   = school,
            student  = student,
            section  = math_section,
            date     = day,
            defaults = {
                "status":    status,
                "marked_by": admin_user,
            }
        )
        if created:
            att_count += 1

print(f"  {att_count} attendance records created.")


# ── 9. Grade Entries (Term 1, MATH + ENG) ────────────────────────────────────

grade_count = 0
for student in all_students:
    for code in ["MATH", "ENG"]:
        section   = sections[(code, 1)]
        enrolment = Enrolment.objects.filter(student=student, section=section).first()
        if not enrolment:
            continue

        for title in ["Assignment 1", "Quiz 1", "Assignment 2"]:
            _, created = GradeEntry.objects.get_or_create(
                school=school, enrolment=enrolment, title=title,
                defaults={
                    "category":      "coursework",
                    "max_marks":     100,
                    "marks_earned":  random.randint(40, 100),
                    "weight":        1,
                    "is_final_exam": False,
                    "date":          random_date_this_year(),
                    "entered_by":    admin_user,
                }
            )
            if created:
                grade_count += 1

        _, created = GradeEntry.objects.get_or_create(
            school=school, enrolment=enrolment, title="Term 1 Final Exam",
            defaults={
                "category":      "exam",
                "max_marks":     100,
                "marks_earned":  random.randint(40, 100),
                "weight":        1,
                "is_final_exam": True,
                "date":          random_date_this_year(),
                "entered_by":    admin_user,
            }
        )
        if created:
            grade_count += 1

print(f"  {grade_count} grade entries created.")


# ── 10. Merits & Demerits ─────────────────────────────────────────────────────

teacher = teachers[0]

for student in random.sample(all_students, 20):
    MeritRecord.objects.get_or_create(
        school=school, student=student, awarded_by=teacher,
        date=random_date_this_year(), reason=random.choice(MERIT_REASONS),
        defaults={
            "category": random.choice(MERIT_CATEGORIES),
            "points":   random.randint(1, 5),
        }
    )

for student in random.sample(all_students, 15):
    DemeritRecord.objects.get_or_create(
        school=school, student=student, awarded_by=teacher,
        date=random_date_this_year(), reason=random.choice(DEMERIT_REASONS),
        defaults={
            "category": random.choice(DEMERIT_CATEGORIES),
            "points":   random.randint(1, 3),
        }
    )

print(f"  Merits and demerits created.")


# ── Done ──────────────────────────────────────────────────────────────────────

print()
print("✅ Seed complete!")
print()
print(f"  School:   {school.name}")
print(f"  Students: {len(all_students)} males (password: student123)")
print(f"  Teachers: {len(teachers)} (password: teacher123)")
print()
print("  Teacher logins:")
for staff in teachers:
    print(f"    {staff.email}  /  teacher123")
print()
print("  Sample student login:")
sample = all_students[0]
print(f"    {sample.user.email}  /  student123")