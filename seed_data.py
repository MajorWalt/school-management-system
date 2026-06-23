"""
Seed script for Edara school management system (Dominica).
Run from project root:
    python manage.py shell -c "exec(open('seed_data.py', encoding='utf-8').read())"
Requires: pip install Faker
"""

import os
import django
import random
import datetime

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from faker import Faker
from faker.providers import BaseProvider

from django.contrib.auth.hashers import make_password
from core.models import School
from accounts.models import User, UserRole
from staff.models import Staff
from students.models import (
    Student, StudentStatusLog, Guardian, StudentGuardian, House
)
from scheduling.models import (
    Form, Homeroom, AcademicYear, TermConfig, Course, Section, Enrolment,
    TimetableSettings, TimetablePeriod, Timetable, TimetableSlot, CYCLE,
)
from attendance.models import Attendance
from grades.models import Evaluation, GradeEntry
from merits.models import MeritRecord, DemeritRecord


# ── Dominica Faker provider ──────────────────────────────────────────────────
class DominicaProvider(BaseProvider):
    """Authentic Dominican names, places and phone numbers."""

    male_first = [
        "Aaron", "Akeem", "Alvin", "Andre", "Anderson", "Brandon", "Curtis",
        "Damian", "Daniel", "Delroy", "Denzel", "Dexter", "Elvis", "Emmanuel",
        "Ezra", "Gideon", "Glenroy", "Isaiah", "Jabari", "Jadon", "Jamal",
        "Javed", "Jevon", "Joel", "Jonas", "Junior", "Kareem", "Kemar",
        "Kenrick", "Kervin", "Khalil", "Kwame", "Lennox", "Levi", "Malik",
        "Marcus", "Nathaniel", "Nigel", "Omar", "Quincy", "Rakeem", "Randy",
        "Rohan", "Sheldon", "Tariq", "Tyrese", "Wendell", "Xavier", "Zane",
    ]
    surnames = [
        "Joseph", "Charles", "Jno Baptiste", "Jno Charles", "Frederick",
        "Casimir", "Laurent", "Augustine", "Paquette", "Lawrence",
        "Shillingford", "Toussaint", "Defoe", "Durand", "Esprit", "Bruney",
        "Carbon", "Royer", "Etienne", "Faustin", "Severin", "Sorhaindo",
        "Lockhart", "Bellot", "Bardouille", "LeBlanc", "Phillip", "Daway",
        "Felix", "Roberts", "Andrew", "Williams", "Allport", "Vidal",
        "Robinson", "Honore", "Magloire", "Prince", "Riviere", "Timothy",
        "Volney", "Fontaine", "Hurtault", "James", "Larocque", "Nicholas",
        "Registe", "Telemaque", "Darroux", "Christmas",
    ]
    communities = [
        "Portsmouth", "Marigot", "Grand Bay", "Soufriere", "Mahaut",
        "Pointe Michel", "Wesley", "Calibishie", "La Plaine", "Castle Bruce",
        "Salisbury", "Mero", "Canefield", "Massacre", "Saint Joseph",
        "Vieille Case", "Colihaut", "Coulibistrie", "Salybia", "Woodford Hill",
        "Trafalgar", "Laudat", "Giraudel", "Newtown", "Pottersville",
        "Goodwill", "Bath Estate", "Fond Cole", "Loubiere", "Wotten Waven",
    ]
    parishes = [
        "Saint Andrew", "Saint David", "Saint George", "Saint John",
        "Saint Joseph", "Saint Luke", "Saint Mark", "Saint Patrick",
        "Saint Paul", "Saint Peter",
    ]
    streets = [
        "Great George Street", "King George V Street", "Independence Street",
        "Old Street", "Turkey Lane", "Cork Street", "Hillsborough Street",
        "Hanover Street", "River Street", "Bath Road", "Kennedy Avenue",
        "Federation Drive", "Castle Street", "Goodwill Road", "Steber Street",
    ]
    religions = [
        "Roman Catholic", "Roman Catholic", "Roman Catholic",
        "Seventh-day Adventist", "Pentecostal", "Baptist", "Methodist",
        "Anglican", "Evangelical", "Jehovah's Witness", "Rastafarian",
    ]
    primary_schools = [
        "Roseau Primary", "Convent Preparatory", "St. Martin Primary",
        "Goodwill Primary", "Newtown Primary", "Pottersville Primary",
        "Wesley Primary", "Portsmouth Primary", "Grand Bay Primary",
        "Marigot Primary", "Massacre Primary", "Castle Bruce Primary",
        "Roosevelt Douglas Primary", "Pierre Charles Primary",
    ]

    def dm_male_name(self):
        return self.random_element(self.male_first)
        pass

    def dm_surname(self):
        return self.random_element(self.surnames)
        pass

    def dm_community(self):
        return self.random_element(self.communities)
        pass

    def dm_parish(self):
        return self.random_element(self.parishes)
        pass

    def dm_phone(self):
        return f"+1 767 {self.numerify('###')}-{self.numerify('####')}"
        pass

    def dm_address(self):
        return f"{self.numerify('##')} {self.random_element(self.streets)}"
        pass

    def dm_religion(self):
        return self.random_element(self.religions)
        pass

    def dm_primary_school(self):
        return self.random_element(self.primary_schools)
        pass


fake = Faker()
fake.add_provider(DominicaProvider)
Faker.seed(42)
random.seed(42)

print("Starting seed...")

# ── Get existing school ───────────────────────────────────────────────────────

school = School.objects.filter(is_active=True).first()
if not school:
    print("No active school found. Create one in the admin first.")
    exit()

print(f"  Using school: {school.name} (slug: {school.slug})")

# ── Helpers ───────────────────────────────────────────────────────────────────

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
RELATIONS = ["Mother", "Father", "Aunt", "Uncle", "Grandmother", "Grandfather", "Guardian"]

used_emails = set(User.objects.values_list("email", flat=True))

def unique_email(first, last, suffix=""):
    base  = f"{first.lower()}.{last.lower()}{suffix}".replace(" ", "")
    email = f"{base}@school.edu"
    n = 1
    while email in used_emails:
        email = f"{base}{n}@school.edu"
        n += 1
    used_emails.add(email)
    return email
    pass

def random_dob():
    return fake.date_of_birth(minimum_age=11, maximum_age=15)
    pass

def random_date_this_year():
    today = datetime.date.today()
    start = datetime.date(today.year, 1, 15)
    if (today - start).days <= 0:
        return start
    return fake.date_between(start_date=start, end_date=today)
    pass


# ── 1. Academic Year + Term Configs ───────────────────────────────────────────

year, created = AcademicYear.objects.get_or_create(
    school=school, name="2024-2025", defaults={"is_current": True}
)
print(f"  {'Created' if created else 'Found'} academic year: {year.name}")

term_data = [
    {"term_number": 1, "name": "Term 1", "has_final_exam": True,  "coursework_weight": 60,  "exam_weight": 40},
    {"term_number": 2, "name": "Term 2", "has_final_exam": False, "coursework_weight": 100, "exam_weight": 0},
    {"term_number": 3, "name": "Term 3", "has_final_exam": True,  "coursework_weight": 60,  "exam_weight": 40},
]
for td in term_data:
    obj, _ = TermConfig.objects.get_or_create(
        academic_year=year, term_number=td["term_number"],
        defaults={
            "name": td["name"], "has_final_exam": td["has_final_exam"],
            "coursework_weight": td["coursework_weight"], "exam_weight": td["exam_weight"],
        }
    )
print(f"  {TermConfig.objects.filter(academic_year=year).count()} term configs ready.")


# ── 2. Sports houses (named after Dominica nature sites) ─────────────────────

house_data = [("Boeri", "Red"), ("Freshwater", "Blue"),
              ("Trafalgar", "Green"), ("Emerald", "Yellow")]
houses = []
for hname, color in house_data:
    h, _ = House.objects.get_or_create(school=school, name=hname, defaults={"color": color})
    houses.append(h)
print(f"  {len(houses)} sports houses ready.")


# ── 3. Forms + Homerooms ─────────────────────────────────────────────────────
#  Form 1 → 101, 102, 103   |   Form 2 → 104, 105, 201  (homeroom = classroom name)

forms_data = [
    ("Form 1", 1, ["101", "102", "103"]),
    ("Form 2", 2, ["104", "105", "201"]),
]
forms          = {}
homerooms      = {}
form_homerooms = {}

for fname, order, hr_names in forms_data:
    f, _ = Form.objects.get_or_create(school=school, name=fname, defaults={"order": order})
    forms[fname] = f
    form_homerooms[fname] = []
    print(f"  Form: {f.name}")
    for hr_name in hr_names:
        hr, _ = Homeroom.objects.get_or_create(
            school=school, name=hr_name, defaults={"form": f}
        )
        homerooms[hr_name] = hr
        form_homerooms[fname].append(hr)
        print(f"    Homeroom: {hr.name}")


# ── 4. Courses ────────────────────────────────────────────────────────────────

course_names = [
    ("Mathematics", "MATH"), ("English Language", "ENG"),
    ("Integrated Science", "SCI"), ("Social Studies", "SS"),
    ("Physical Education", "PE"), ("Information Technology", "IT"),
    ("Art & Design", "ART"), ("French", "FRE"),
]
courses = {}
for name, code in course_names:
    c, _ = Course.objects.get_or_create(
        school=school, name=name, defaults={"code": code, "active": True}
    )
    courses[code] = c
print(f"  {len(courses)} courses ready.")


# ── 5. Teachers (Dominican names) ────────────────────────────────────────────

teacher_specs = [
    ("Mathematics",        "Mathematics Teacher", "Mathematics"),
    ("Languages",          "English Teacher",     "English Language"),
    ("Sciences",           "Science Teacher",     "Integrated Science"),
    ("Social Studies",     "History Teacher",     "Social Studies"),
    ("Physical Education", "PE Teacher",          "Physical Education"),
    ("Technology",         "IT Teacher",          "Information Technology"),
    ("Arts",               "Art Teacher",         "Art & Design"),
    ("Languages",          "French Teacher",      "French"),
]
teachers = []
for i, (dept, role_title, spec) in enumerate(teacher_specs, start=1):
    first = fake.dm_male_name()
    last  = fake.dm_surname()
    email = unique_email(first, last, ".staff")

    user, _ = User.objects.get_or_create(
        email=email,
        defaults={"first_name": first, "last_name": last,
                  "password": make_password("teacher123"), "is_active": True}
    )
    UserRole.objects.get_or_create(user=user, school=school, role="teacher")

    staff, _ = Staff.objects.get_or_create(
        school=school, employee_number=f"T{i:03d}",
        defaults={
            "user": user, "first_name": first, "last_name": last, "gender": "M",
            "email_work": email, "department": dept, "role_title": role_title,
            "subject_specialisation": spec, "hire_date": datetime.date(2020, 9, 1),
            "active": True,
        }
    )
    teachers.append(staff)
print(f"  {len(teachers)} teachers ready.")


# ── 6. Sections (per form, per course, per term) ─────────────────────────────

course_teacher_map = {"MATH": 0, "ENG": 1, "SCI": 2, "SS": 3,
                      "PE": 4, "IT": 5, "ART": 6, "FRE": 7}
sections = {}
for fname, f in forms.items():
    hr_names = [hr.name for hr in form_homerooms[fname]]
    for code, course in courses.items():
        teacher = teachers[course_teacher_map.get(code, 0)]
        for term_num in [1, 2, 3]:
            sec, _ = Section.objects.get_or_create(
                school=school, course=course, academic_year=year,
                term_number=term_num, form=f,
                defaults={"teacher": teacher, "room": random.choice(hr_names)}
            )
            sections[(fname, code, term_num)] = sec
print(f"  {len(sections)} sections ready.")


# ── 7. Students (all male; 20–28 per homeroom) + Guardians ───────────────────

all_students   = []
form_students  = {fname: [] for fname in forms}
student_counter = 1

for fname, f in forms.items():
    for homeroom in form_homerooms[fname]:
        for _ in range(random.randint(20, 28)):
            first = fake.dm_male_name()
            last  = fake.dm_surname()
            email = unique_email(first, last, f".{homeroom.name}")
            sid   = f"2025{student_counter:04d}"

            user, _ = User.objects.get_or_create(
                email=email,
                defaults={"first_name": first, "last_name": last,
                          "password": make_password("student123"), "is_active": True}
            )
            UserRole.objects.get_or_create(user=user, school=school, role="student")

            community = fake.dm_community()
            student, created = Student.objects.get_or_create(
                school=school, student_id=sid,
                defaults={
                    "user": user,
                    "first_name": first,
                    "middle_name": fake.dm_male_name(),
                    "last_name": last,
                    "gender": "M",
                    "date_of_birth": random_dob(),
                    "nationality": "Dominican",
                    "religion": fake.dm_religion(),
                    "house": random.choice(houses),
                    "phone": fake.dm_phone(),
                    "email": email,
                    "address": fake.dm_address(),
                    "city": "Roseau",
                    "parish": fake.dm_parish(),
                    "community": community,
                    "form": f,
                    "homeroom": homeroom,
                    "admission_date": datetime.date(2024, 9, 3),
                    "previous_school": fake.dm_primary_school(),
                    "emis_id": fake.numerify("DM######"),
                    "father_name": f"{fake.dm_male_name()} {last}",
                    "mother_name": f"{fake.first_name_female()} {fake.dm_surname()}",
                    "lives_with": random.choice(["Both parents", "Mother", "Father", "Guardian"]),
                    "emergency_contact_name": f"{fake.first_name_female()} {last}",
                    "emergency_relation": random.choice(RELATIONS),
                    "emergency_phone_1": fake.dm_phone(),
                    "emergency_phone_2": fake.dm_phone(),
                    "doctor_name": f"Dr. {fake.dm_surname()}",
                    "doctor_phone": fake.dm_phone(),
                    "notes": "",
                    # ── Confirm column types before enabling these ──
                    # "cohort_grade": fname,
                    # "cohort_year": 2024,
                    # "repeated": False,
                    # "gsna_year": 2024,
                    # "gsna_award": "Pass",
                    # "gsna_english": "B", "gsna_mathematics": "B",
                    # "gsna_science": "C", "gsna_social_studies": "B",
                }
            )

            if created:
                StudentStatusLog.objects.create(
                    student=student, status="enrolled",
                    change_date=datetime.date(2024, 9, 3),
                    reason="Initial enrolment", changed_by=user,
                )

                # One primary guardian per student
                g_first = fake.first_name_female()
                g_last  = last
                guardian, _ = Guardian.objects.get_or_create(
                    school=school, first_name=g_first, last_name=g_last,
                    phone=fake.dm_phone(),
                    defaults={"email": fake.unique.email(),
                              "address": f"{fake.dm_address()}, {community}"}
                )
                StudentGuardian.objects.get_or_create(
                    student=student, guardian=guardian,
                    defaults={"relationship": "Mother",
                              "is_primary": True, "can_pickup": True}
                )

            all_students.append(student)
            form_students[fname].append(student)
            student_counter += 1

    print(f"  {fname}: {len(form_students[fname])} students.")
print(f"  {len(all_students)} students ready in total.")


# ── 8. Enrolments (each student into their own form's sections) ──────────────

enrolment_count = 0
for fname, students in form_students.items():
    form_sections = [sec for (sfn, code, term), sec in sections.items() if sfn == fname]
    for student in students:
        for section in form_sections:
            _, created = Enrolment.objects.get_or_create(student=student, section=section)
            if created:
                enrolment_count += 1
print(f"  {enrolment_count} enrolments created.")


# ── 9. Attendance — homeroom-based, last 10 school days ──────────────────────

admin_user = User.objects.filter(is_superuser=True).first()
today = datetime.date.today()

school_days = []
d = today
while len(school_days) < 10:
    if d.weekday() < 5:
        school_days.append(d)
    d -= datetime.timedelta(days=1)

att_count = 0
for hr_name, homeroom in homerooms.items():
    hr_students = [s for s in all_students if s.homeroom_id == homeroom.id]
    for student in hr_students:
        for day in school_days:
            roll = random.random()
            if roll < 0.90:
                continue                       # present = default, not stored
            status = "absent" if roll < 0.97 else "late"
            Attendance.objects.get_or_create(
                school=school, student=student, homeroom=homeroom, date=day,
                defaults={"status": status, "marked_by": admin_user}
            )
            att_count += 1
print(f"  {att_count} attendance exception records created.")


# ── 10. Evaluations + Grade Entries (Term 1, 3 subjects, both forms) ─────────

GRADED_SUBJECTS = ["MATH", "ENG", "SCI"]
eval_definitions = [
    {"title": "Assignment 1",      "category": "coursework", "subcategory": "assignment", "max_marks": 100, "weight": 1, "is_final_exam": False},
    {"title": "Quiz 1",            "category": "coursework", "subcategory": "quiz",       "max_marks": 50,  "weight": 1, "is_final_exam": False},
    {"title": "Assignment 2",      "category": "coursework", "subcategory": "assignment", "max_marks": 100, "weight": 1, "is_final_exam": False},
    {"title": "Term 1 Final Exam", "category": "exam",       "subcategory": "final_exam", "max_marks": 100, "weight": 2, "is_final_exam": True},
]
grade_count = 0
eval_count  = 0
for fname in forms:
    for code in GRADED_SUBJECTS:
        section = sections[(fname, code, 1)]
        evals = []
        for ed in eval_definitions:
            ev, created = Evaluation.objects.get_or_create(
                school=school, section=section, title=ed["title"],
                defaults={
                    "category": ed["category"], "subcategory": ed["subcategory"],
                    "max_marks": ed["max_marks"], "weight": ed["weight"],
                    "is_final_exam": ed["is_final_exam"],
                    "date": random_date_this_year(), "created_by": admin_user,
                }
            )
            evals.append(ev)
            if created:
                eval_count += 1

        enrolled = [e.student for e in Enrolment.objects.filter(section=section).select_related("student")]
        for student in enrolled:
            for ev in evals:
                is_absent = random.random() < 0.10
                marks = None if is_absent else round(random.uniform(40, ev.max_marks), 1)
                _, created = GradeEntry.objects.get_or_create(
                    evaluation=ev, student=student,
                    defaults={"school": school, "marks_earned": marks,
                              "is_absent": is_absent, "entered_by": admin_user}
                )
                if created:
                    grade_count += 1
print(f"  {eval_count} evaluations created.")
print(f"  {grade_count} grade entries created.")


# ── 11. Merits & Demerits (field is `count`, not `points`) ───────────────────

teacher = teachers[0]
for student in random.sample(all_students, 20):
    MeritRecord.objects.get_or_create(
        school=school, student=student, awarded_by=teacher,
        date=random_date_this_year(), reason=random.choice(MERIT_REASONS),
        defaults={"category": random.choice(MERIT_CATEGORIES), "count": random.randint(1, 5)}
    )
for student in random.sample(all_students, 15):
    DemeritRecord.objects.get_or_create(
        school=school, student=student, awarded_by=teacher,
        date=random_date_this_year(), reason=random.choice(DEMERIT_REASONS),
        defaults={"category": random.choice(DEMERIT_CATEGORIES), "count": random.randint(1, 3)}
    )
print("  Merits and demerits created.")


# ── 12. Timetable settings + bell schedule (times from St. Mary's sheet) ─────

TimetableSettings.objects.update_or_create(
    school=school,
    defaults={"mode": CYCLE, "cycle_length": 6,
              "anchor_date": datetime.date(2024, 9, 3)}
)
print("  Timetable settings set (6-day cycle).")

period_data = [
    ("Home room", 1, datetime.time(7, 45),  datetime.time(8, 0),   True),
    ("Period 1",  2, datetime.time(8, 0),   datetime.time(8, 40),  False),
    ("Period 2",  3, datetime.time(8, 40),  datetime.time(9, 20),  False),
    ("Period 3",  4, datetime.time(9, 20),  datetime.time(10, 0),  False),
    ("Period 4",  5, datetime.time(10, 0),  datetime.time(10, 40), False),
    ("Break",     6, datetime.time(10, 40), datetime.time(11, 0),  True),
    ("Period 5",  7, datetime.time(11, 0),  datetime.time(11, 40), False),
    ("Period 6",  8, datetime.time(11, 40), datetime.time(12, 20), False),
    ("Period 7",  9, datetime.time(12, 20), datetime.time(13, 0),  False),
]
for name, order, start, end, is_break in period_data:
    TimetablePeriod.objects.get_or_create(
        school=school, order=order,
        defaults={"name": name, "start_time": start, "end_time": end, "is_break": is_break}
    )
print(f"  {len(period_data)} timetable periods ready.")


# ── 13. Term 1 timetable per form (fill the grid + one split period) ─────────

teaching_periods = list(TimetablePeriod.objects.filter(school=school, is_break=False).order_by("order"))
cycle_days    = [1, 2, 3, 4, 5, 6]
subject_codes = list(courses.keys())

slot_count = 0
for fname, f in forms.items():
    timetable, _ = Timetable.objects.get_or_create(
        school=school, form=f, academic_year=year, term_number=1
    )
    idx = 0
    for day in cycle_days:
        for period in teaching_periods:
            code = subject_codes[idx % len(subject_codes)]
            section = sections[(fname, code, 1)]
            _, created = TimetableSlot.objects.get_or_create(
                timetable=timetable, day_number=day, period=period, section=section,
                defaults={"school": school}
            )
            if created:
                slot_count += 1
            idx += 1

    # Demo split/switch period: Day 1, last teaching period gets a 2nd subject.
    _, created = TimetableSlot.objects.get_or_create(
        timetable=timetable, day_number=1, period=teaching_periods[-1],
        section=sections[(fname, "ART", 1)], defaults={"school": school}
    )
    if created:
        slot_count += 1
print(f"  {slot_count} timetable slots created (Term 1, both forms).")


# ── Done ──────────────────────────────────────────────────────────────────────

print()
print("Seed complete!")
print(f"  School:    {school.name}")
print(f"  Students:  {len(all_students)} males (password: student123)")
print(f"  Teachers:  {len(teachers)} (password: teacher123)")
print(f"  Forms:     Form 1 (101, 102, 103)  |  Form 2 (104, 105, 201)")
print(f"  Houses:    {', '.join(h.name for h in houses)}")
print(f"  Timetable: 6-day cycle, Term 1 filled for both forms")
print()
print("  Teacher logins:")
for staff in teachers:
    print(f"    {staff.email_work}  /  teacher123")
print(f"  Sample student login: {all_students[0].user.email}  /  student123")