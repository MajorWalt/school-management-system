"""
Django management command to seed the database with comprehensive school data.
Creates 2 academic years (2024-2025 and 2025-2026) with full timetable, students, and grades.
"""

import random
from datetime import datetime, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from django.db import transaction
from faker import Faker

from core.models import School
from accounts.models import User, UserRole
from staff.models import Staff
from students.models import Student, StudentStatusLog, House
from scheduling.models import (
    Form,
    Homeroom,
    AcademicYear,
    TermConfig,
    Course,
    Section,
    Enrolment,
    TimetableSettings,
    TimetablePeriod,
    Timetable,
    TimetableSlot,
    YearPlacement,
)
from attendance.models import Attendance
from grades.models import Evaluation, GradeEntry, GradeWindow
from merits.models import MeritRecord, DemeritRecord

fake = Faker()
Faker.seed(42)
random.seed(42)

DOMINICAN_FIRST_NAMES_MALE = [
    "Aaron",
    "Akeem",
    "Alvin",
    "Anthony",
    "Bernard",
    "Brandan",
    "Carlton",
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
    "Frederick",
    "Gideon",
    "Glenroy",
    "Gordon",
    "Gregory",
    "Hayden",
    "Henry",
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
    "Julius",
    "Juno",
    "Justin",
    "Kelvin",
    "Kevin",
    "Kyle",
    "Liam",
    "Marcus",
    "Michael",
    "Nathan",
    "Nicholas",
    "Noah",
    "Oliver",
    "Patrick",
    "Paul",
    "Peter",
    "Raymond",
    "Richard",
    "Robert",
    "Ryan",
    "Samuel",
    "Sebastian",
    "Stephen",
    "Thomas",
    "Timothy",
    "Trevor",
    "Victor",
    "Vincent",
    "Walter",
    "William",
    "Xavier",
    "Zachary",
]

DOMINICAN_FIRST_NAMES_FEMALE = [
    "Abigail",
    "Alexis",
    "Alicia",
    "Amanda",
    "Amy",
    "Andrea",
    "Angela",
    "Anita",
    "Anna",
    "Ashley",
    "Barbara",
    "Brenda",
    "Candice",
    "Caroline",
    "Catherine",
    "Cecilia",
    "Charlotte",
    "Christina",
    "Christine",
    "Clara",
    "Claudia",
    "Crystal",
    "Cynthia",
    "Danielle",
    "Deborah",
    "Diana",
    "Diane",
    "Donna",
    "Dorothy",
    "Elizabeth",
    "Emily",
    "Emma",
    "Francine",
    "Grace",
    "Hannah",
    "Helen",
    "Hilary",
    "Isabella",
    "Jane",
    "Janet",
    "Janice",
    "Jennifer",
    "Jessica",
    "Jestina",
    "Joanna",
    "Josephine",
    "Joyce",
    "Judith",
    "Julia",
    "Julienne",
    "Karen",
    "Katherine",
    "Kathleen",
    "Kelly",
    "Kimberly",
    "Laura",
    "Lauren",
    "Linda",
    "Lisa",
    "Margaret",
    "Maria",
    "Marie",
    "Martha",
    "Mary",
    "Melissa",
    "Michelle",
    "Monica",
    "Nancy",
    "Natalie",
    "Nicole",
    "Olivia",
    "Patricia",
    "Rachel",
    "Rebecca",
    "Rosa",
    "Ruth",
    "Samantha",
    "Sandra",
    "Sarah",
    "Sharon",
    "Sophia",
    "Stephanie",
    "Susan",
    "Teresa",
    "Theresa",
    "Victoria",
    "Virginia",
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
    "Barrett",
    "Barry",
    "Bartlett",
    "Barton",
    "Bass",
    "Bates",
    "Bath",
    "Batts",
    "Baxter",
    "Beale",
    "Beard",
    "Bearden",
    "Beaver",
    "Beavers",
    "Beck",
    "Becker",
    "Beckham",
    "Beckley",
    "Bell",
    "Benjamin",
    "Bennett",
    "Bernard",
    "Berry",
    "Black",
    "Blair",
    "Blake",
    "Bolton",
    "Bostic",
    "Boucher",
    "Bowman",
    "Boyd",
    "Bradley",
    "Brady",
    "Brathwaite",
    "Bridges",
    "Brooks",
    "Brown",
    "Bruce",
    "Bruno",
    "Bryan",
    "Bryant",
    "Burnett",
    "Burns",
    "Burton",
    "Butler",
    "Caesar",
    "Campbell",
    "Carbon",
    "Carr",
    "Carroll",
    "Carter",
    "Charles",
    "Christian",
    "Clarke",
    "Clarkson",
    "Cole",
    "Coleman",
    "Collins",
    "Cooper",
    "Cox",
    "Crawford",
    "Cross",
    "Cruz",
    "Dailey",
    "Daniel",
    "Darroux",
    "David",
    "Davidson",
    "Davis",
    "Dawson",
    "Dean",
    "Delsol",
    "Dennis",
    "Dixon",
    "Douglas",
    "Drigo",
    "Duncan",
    "Durand",
    "Edwards",
    "Elliott",
    "Ellis",
    "Emmanuel",
    "Evans",
    "Fadelle",
    "Felix",
    "Ferdinand",
    "Ferguson",
    "Fields",
    "Fisher",
    "Flores",
    "Fontaine",
    "Ford",
    "Foster",
    "Francis",
    "Frank",
    "Franklin",
    "Frederick",
    "Freeman",
    "Gabriel",
    "Garcia",
    "George",
    "Gibson",
    "Gilbert",
    "Gill",
    "Gordon",
    "Graham",
    "Grant",
    "Gray",
    "Green",
    "Greene",
    "Gregory",
    "Griffin",
    "Guiste",
    "Hamilton",
    "Harris",
    "Harrison",
    "Henderson",
    "Henry",
    "Hill",
    "Hilton",
    "Hodge",
    "Holmes",
    "Howard",
    "Hudson",
    "Hughes",
    "Hunt",
    "Hunter",
    "Isaac",
    "Jackson",
    "Jacob",
    "James",
    "Jean",
    "Jno Baptiste",
    "John",
    "Johnson",
    "Jones",
    "Jordan",
    "Joseph",
    "Jules",
    "Julius",
    "King",
    "Knight",
    "Lambert",
    "Lawrence",
    "Lee",
    "Lewis",
    "Lloyd",
    "Long",
    "Lopez",
    "Louis",
    "Lynch",
    "Martin",
    "Mason",
    "Matthew",
    "Matthews",
    "McKenzie",
    "Mills",
    "Mitchell",
    "Moore",
    "Morgan",
    "Morris",
    "Moses",
    "Murphy",
    "Murray",
    "Nelson",
    "Nicholas",
    "Norton",
    "Oliver",
    "Parker",
    "Pascal",
    "Patrick",
    "Paul",
    "Peters",
    "Philip",
    "Pierre",
    "Powell",
    "Price",
    "Reid",
    "Richards",
    "Richardson",
    "Riley",
    "Rivers",
    "Roberts",
    "Robinson",
    "Rogers",
    "Rose",
    "Ross",
    "Royer",
    "Russell",
    "Samuel",
    "Sanchez",
    "Sanders",
    "Scott",
    "Seaman",
    "Shillingford",
    "Simon",
    "Simpson",
    "Smith",
    "St. Hilaire",
    "St. Jean",
    "St. Rose",
    "Stephens",
    "Stevens",
    "Stewart",
    "Sullivan",
    "Taylor",
    "Thomas",
    "Thompson",
    "Toussaint",
    "Turner",
    "Walker",
    "Wallace",
    "Walsh",
    "Walter",
    "Ward",
    "Warner",
    "Warren",
    "Washington",
    "Watson",
    "Webb",
    "Wellington",
    "Wells",
    "White",
    "Williams",
    "Wilson",
    "Winston",
    "Woods",
    "Wright",
    "Young",
]

# Course data from your provided list
COURSES_DATA = """Agricultural Science 1,AGRI1
Agricultural Science 2,AGRI2
Agricultural Science 3,AGRI3
Agricultural Science 4,AGRI4
Agricultural Science 5,AGRI5
Art and Craft 1,ART1
Art and Craft 2,ART2
Art and Craft 3,ART3
Biology 3,BIO3
Biology 4,BIO4
Biology 5,BIO5
Building Technology 3,BT3
Building Technology 4,BT4
Building Technology 5,BT5
Caribbean History 1,HIS1
Caribbean History 2,HIS2
Caribbean History 3,HIS3
Caribbean History 4,HIS4
Caribbean History 5,HIS5
Chemistry 3,CHEM3
Chemistry 4,CHEM4
Chemistry 5,CHEM5
English 1,ENG1
English 2,ENG2
English 3,ENG3
English 4,ENG4
English 5,ENG5
French 1,FRE1
French 2,FRE2
French 3,FRE3
French 4,FRE4
French 5,FREC5
French for Life 5,FREL5
Geography 3,GEO3
Geography 4,GEO4
Geography 5,GEO5
Health and Family Life Education 2,HFLE2
Health and Family Life Education 3,HFLE3
Human and Social Biology 3,HSB3
Human and Social Biology 4,HSB4
Human and Social Biology 5,HSB5
Information Technology 1,IT1
Information Technology 2,IT2
Information Technology 3,IT3
Information Technology 4,IT4
Information Technology 5,IT5
Integrated Science 1,INT1
Integrated Science 2,INT2
Literature 1,LIT1
Literature 2,LIT2
Literature 3,LIT3
Mathematics 1,MAT1
Mathematics 2,MAT2
Mathematics 3,MAT3
Mathematics 4,MAT4
Mathematics 5,MAT5
Music 1,MUS1
Music 2,MUS2
Music 3,MUS3
Physical Education 1,PE1
Physical Education 2,PE2
Physics 3,PHY3
Physics 4,PHY4
Physics 5,PHY5
Principles of Accounts 3,POA3
Principles of Accounts 4,POA4
Principles of Accounts 5,POA5
Principles of Business 3,POB3
Principles of Business 4,POB4
Principles of Business 5,POB5
Religion 1,REL1
Religion 2,REL2
Religion 3,REL3
Religion 4,REL4
Religion 5,REL5
Spanish 1,SPA1
Spanish 2,SPA2
Spanish 3,SPA3
Spanish 4,SPA4
Spanish 5,SPAC5
Spanish for Life 5,SPAL5
Technical Drawing 3,TD3
Technical Drawing 4,TD4
Technical Drawing 5,TD5"""


class Command(BaseCommand):
    help = "Seed the database with comprehensive school data for 2024-2025 and 2025-2026"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("\n" + "=" * 80))
        self.stdout.write(self.style.SUCCESS("SEEDING ST. MARY'S ACADEMY - COMPREHENSIVE DATA"))
        self.stdout.write(self.style.SUCCESS("=" * 80 + "\n"))

        with transaction.atomic():
            school = self.create_school()

            # Create both academic years
            year_2024 = self.create_academic_year(school, "2024-2025", is_current=False)
            year_2025 = self.create_academic_year(school, "2025-2026", is_current=True)

            # Create houses
            houses = self.create_houses(school)

            # Create forms and homerooms
            forms = self.create_forms(school)
            homerooms = self.create_homerooms(school, forms)

            # Create timetable settings
            self.create_timetable_settings(school)
            periods = self.create_timetable_periods(school)

            # Create teachers
            teachers = self.create_teachers(school)
            admin_user = User.objects.filter(email="wgreenaway@smadominica.com").first()
            if not admin_user:
                admin_user = list(teachers.values())[0].user

            # Create courses
            courses = self.create_courses(school)

            # Create students for 2024-2025
            students_2024 = self.create_students_year1(school, forms, homerooms, year_2024, houses, admin_user)

            # Create sections for 2024-2025
            sections_2024 = self.create_sections(school, year_2024, forms, courses, teachers)

            # Create enrolments for 2024-2025
            self.create_enrolments(school, year_2024, forms, students_2024, sections_2024)

            # Create timetables for 2024-2025
            self.create_timetables(school, year_2024, forms, sections_2024, periods)

            # Create grade windows for 2024-2025
            self.create_grade_windows(school, year_2024, forms)

            # Create evaluations and grades for 2024-2025
            self.create_evaluations_and_grades(school, year_2024, sections_2024)

            # Create attendance for 2024-2025
            self.create_attendance(school, year_2024, students_2024)

            # Create merits and demerits for 2024-2025
            self.create_merits_and_demerits(school, year_2024, students_2024, teachers)

            # Promote students to 2025-2026
            students_2025 = self.promote_students(school, forms, homerooms, year_2024, year_2025, houses, admin_user)

            # Create sections for 2025-2026
            sections_2025 = self.create_sections(school, year_2025, forms, courses, teachers)

            # Create enrolments for 2025-2026
            self.create_enrolments(school, year_2025, forms, students_2025, sections_2025)

            # Create timetables for 2025-2026
            self.create_timetables(school, year_2025, forms, sections_2025, periods)

            # Create grade windows for 2025-2026
            self.create_grade_windows(school, year_2025, forms)

            # Create evaluations and grades for 2025-2026 (Term 1 and 2 only)
            self.create_evaluations_and_grades(school, year_2025, sections_2025, terms=[1, 2])

            # Create attendance for 2025-2026
            self.create_attendance(school, year_2025, students_2025)

            # Create merits and demerits for 2025-2026
            self.create_merits_and_demerits(school, year_2025, students_2025, teachers)

        self.print_summary()

    def create_school(self):
        school, created = School.objects.get_or_create(name="Saint Mary's Academy", defaults={"is_active": True})
        if created:
            self.stdout.write(f"[+] Created school: {school.name}")
        else:
            self.stdout.write(f"[+] Using existing school: {school.name}")
        return school

    def create_academic_year(self, school, name, is_current=False):
        year_start = 2024 if "2024" in name else 2025
        year, created = AcademicYear.objects.get_or_create(
            school=school,
            name=name,
            defaults={
                "is_current": is_current,
                "start_date": datetime(year_start, 9, 3).date(),
                "end_date": datetime(year_start + 1, 6, 30).date(),
            },
        )
        if created:
            self.stdout.write(f"[+] Created academic year: {year.name}")

        # Term 1: Has exam (60/40)
        # Term 2: No exam (100/0)
        # Term 3: Has exam (60/40)
        terms = [
            {"term_number": 1, "name": "Term 1", "has_exam": True, "cw": 60, "ex": 40, "start": (year_start, 9, 3), "end": (year_start, 11, 22)},
            {"term_number": 2, "name": "Term 2", "has_exam": False, "cw": 100, "ex": 0, "start": (year_start + 1, 1, 6), "end": (year_start + 1, 3, 28)},
            {"term_number": 3, "name": "Term 3", "has_exam": True, "cw": 60, "ex": 40, "start": (year_start + 1, 4, 7), "end": (year_start + 1, 6, 30)},
        ]

        for term_data in terms:
            TermConfig.objects.get_or_create(
                academic_year=year,
                term_number=term_data["term_number"],
                defaults={
                    "name": term_data["name"],
                    "has_final_exam": term_data["has_exam"],
                    "coursework_weight": term_data["cw"],
                    "exam_weight": term_data["ex"],
                    "start_date": datetime(*term_data["start"]).date(),
                    "end_date": datetime(*term_data["end"]).date(),
                },
            )

        return year

    def create_forms(self, school):
        forms = {}
        for form_num in range(1, 6):
            form, created = Form.objects.get_or_create(
                school=school,
                name=f"Form {form_num}",
                defaults={"order": form_num},
            )
            forms[form_num] = form
        self.stdout.write(f"[+] Created 5 forms")
        return forms

    def create_homerooms(self, school, forms):
        # Form 1: 101, 102, 103
        # Form 2: 104, 105, 201
        # Form 3: 202, 203, wa5
        # Form 4: 204, 205, 206
        # Form 5: wa1, wa2, wa3
        homeroom_mapping = {
            1: ["101", "102", "103"],
            2: ["104", "105", "201"],
            3: ["202", "203", "wa5"],
            4: ["204", "205", "206"],
            5: ["wa1", "wa2", "wa3"],
        }

        homerooms = {}
        for form_num, homeroom_names in homeroom_mapping.items():
            form = forms[form_num]
            for homeroom_name in homeroom_names:
                homeroom, created = Homeroom.objects.get_or_create(
                    school=school,
                    form=form,
                    name=homeroom_name,
                )
                homerooms[(form_num, homeroom_name)] = homeroom

        self.stdout.write(f"[+] Created {len(homerooms)} homerooms")
        return homerooms

    def create_houses(self, school):
        house_names = ["Garvey", "Marley", "Mandela", "Pan"]
        houses = []
        for name in house_names:
            house, created = House.objects.get_or_create(
                school=school, name=name, defaults={"color": "#" + "".join([random.choice("0123456789ABCDEF") for _ in range(6)])}
            )
            houses.append(house)
        self.stdout.write(f"[+] Created {len(houses)} houses")
        return houses

    def create_timetable_settings(self, school):
        settings, created = TimetableSettings.objects.get_or_create(
            school=school,
            defaults={
                "mode": "cycle",
                "cycle_length": 6,
                "anchor_date": datetime(2024, 9, 3).date(),
            },
        )
        self.stdout.write(f"[+] Created timetable settings (6-day cycle)")
        return settings

    def create_timetable_periods(self, school):
        # Create 7 periods
        periods = []
        for i in range(1, 8):
            period, created = TimetablePeriod.objects.get_or_create(
                school=school,
                order=i,
                defaults={
                    "name": f"Period {i}",
                    "is_break": False,
                },
            )
            periods.append(period)
        self.stdout.write(f"[+] Created {len(periods)} timetable periods")
        return periods

    def create_teachers(self, school):
        """Create 40 teachers with diverse subjects"""
        teachers = {}
        teacher_names = [
            ("Helen", "Toulon"),
            ("Andre", "Desbonne"),
            ("Maria", "Marie"),
            ("Miguel", "Lopez"),
            ("Gabriela", "Maffei"),
            ("Julia", "Faddoul"),
            ("Kathy", "St. Hilaire"),
            ("Rachel", "Paul"),
            ("Delwin", "Elwin"),
            ("Richard", "Joseph"),
            ("Emily", "Massicott"),
            ("Robert", "Stevens"),
            ("Sharon", "Burgins"),
            ("Julie", "Paul"),
            ("Sandra", "Isles"),
            ("John", "Samuel"),
            ("Teresa", "Francis"),
            ("Jane", "David"),
            ("Anne", "Proctor"),
            ("Gina", "Winston"),
            ("Carol", "Lloyd"),
            ("Nancy", "Christian"),
            ("Beverly", "Figaro"),
            ("Harold", "Boland"),
            ("Scott", "Dailey"),
            ("James", "Mills"),
            ("Sarah", "Charles"),
            ("George", "Caesar"),
            ("Monica", "Moses"),
            ("Christine", "Philogene"),
            ("Daniel", "Lewis"),
            ("Peter", "Stephens"),
            ("Mary", "Anderson"),
            ("Thomas", "Brown"),
            ("Patricia", "Clark"),
            ("Michael", "Davis"),
            ("Jennifer", "Evans"),
            ("William", "Fisher"),
            ("Linda", "Green"),
            ("Robert", "Hill"),
        ]

        for idx, (first_name, last_name) in enumerate(teacher_names):
            email = f"{first_name[0].lower()}{last_name.lower()}@smadominica.com"

            user, _ = User.objects.get_or_create(
                email=email,
                defaults={
                    "first_name": first_name,
                    "last_name": last_name,
                    "password": make_password("teacher123"),
                    "is_active": True,
                },
            )

            staff, created = Staff.objects.get_or_create(
                school=school,
                user=user,
                defaults={
                    "first_name": first_name,
                    "last_name": last_name,
                    "employee_number": f"SMA{idx + 1:03d}",
                    "active": True,
                },
            )

            if created:
                UserRole.objects.get_or_create(
                    user=user,
                    school=school,
                    defaults={"role": "teacher"},
                )

            teachers[email] = staff

        self.stdout.write(f"[+] Created {len(teachers)} teachers")
        return teachers

    def create_courses(self, school):
        """Create all courses from the course data"""
        courses = {}

        for line in COURSES_DATA.strip().split("\n"):
            name, code = line.split(",")

            # Extract form number from code (e.g., "AGRI1" -> 1)
            form_num = None
            for char in code:
                if char.isdigit():
                    form_num = int(char)
                    break

            course, created = Course.objects.get_or_create(
                school=school,
                code=code,
                defaults={
                    "name": name,
                    "short_description": code,
                    "active": True,
                },
            )
            courses[code] = course

        self.stdout.write(f"[+] Created {len(courses)} courses")
        return courses

    def create_students_year1(self, school, forms, homerooms, academic_year, houses, admin_user):
        """Create students for 2024-2025 (15-20 per homeroom)"""
        students = []

        for (form_num, homeroom_name), homeroom in homerooms.items():
            form = forms[form_num]
            num_students = random.randint(15, 20)

            for i in range(num_students):
                gender = random.choice(["M", "F"])
                first_names = DOMINICAN_FIRST_NAMES_MALE if gender == "M" else DOMINICAN_FIRST_NAMES_FEMALE
                first_name = random.choice(first_names)
                last_name = random.choice(DOMINICAN_LAST_NAMES)

                student_id = f"{academic_year.name[:4]}-{form_num}{homeroom_name}-{i + 1:02d}"
                email = f"{first_name.lower()}.{last_name.lower()}{i:02d}@student.smadominica.com"

                user, _ = User.objects.get_or_create(
                    email=email,
                    defaults={
                        "first_name": first_name,
                        "last_name": last_name,
                        "password": make_password("student123"),
                        "is_active": True,
                    },
                )

                UserRole.objects.get_or_create(
                    user=user,
                    school=school,
                    defaults={"role": "student"},
                )

                student, created = Student.objects.get_or_create(
                    school=school,
                    student_id=student_id,
                    defaults={
                        "first_name": first_name,
                        "last_name": last_name,
                        "form": form,
                        "homeroom": homeroom,
                        "gender": gender,
                        "date_of_birth": fake.date_of_birth(minimum_age=10 + form_num, maximum_age=12 + form_num),
                        "admission_date": academic_year.start_date,
                        "house": random.choice(houses),
                    },
                )

                if created:
                    StudentStatusLog.objects.create(
                        student=student,
                        academic_year=academic_year,
                        status="enrolled",
                        change_date=academic_year.start_date,
                        reason="Initial enrolment",
                    )

                    YearPlacement.objects.create(
                        student=student,
                        academic_year=academic_year,
                        form=form,
                        homeroom=homeroom,
                        outcome="continuing",
                        recorded_by=admin_user,
                    )

                    students.append(student)

        self.stdout.write(f"[+] Created {len(students)} students for 2024-2025")
        return students

    def promote_students(self, school, forms, homerooms, year_2024, year_2025, houses, admin_user):
        """Promote students from 2024-2025 to 2025-2026"""
        students_2025 = []

        # Get all students from 2024-2025
        placements_2024 = YearPlacement.objects.filter(academic_year=year_2024)

        for placement in placements_2024:
            student = placement.student
            old_form_num = placement.form.order

            # Form 5 students: 90% graduate, 10% do not graduate
            if old_form_num == 5:
                if random.random() < 0.90:
                    # Graduate
                    YearPlacement.objects.create(
                        student=student,
                        academic_year=year_2025,
                        form=placement.form,
                        homeroom=None,
                        outcome="graduated",
                        recorded_by=admin_user,
                    )
                    StudentStatusLog.objects.create(
                        student=student,
                        academic_year=year_2025,
                        status="graduated",
                        change_date=year_2025.start_date,
                        reason="Completed Form 5",
                    )
                else:
                    # Do not graduate
                    YearPlacement.objects.create(
                        student=student,
                        academic_year=year_2025,
                        form=placement.form,
                        homeroom=None,
                        outcome="not_graduated",
                        recorded_by=admin_user,
                    )
                    StudentStatusLog.objects.create(
                        student=student,
                        academic_year=year_2025,
                        status="not_graduated",
                        change_date=year_2025.start_date,
                        reason="Did not meet graduation requirements",
                    )
            else:
                # Other forms: 5% repeat, 95% promote
                if random.random() < 0.05:
                    # Repeat
                    new_form = placement.form
                    # Try to keep same homeroom if possible
                    old_homeroom_name = placement.homeroom.name if placement.homeroom else None
                    new_homeroom = homerooms.get((old_form_num, old_homeroom_name))
                    if not new_homeroom:
                        # Pick random homeroom from same form
                        form_homerooms = [hr for (fn, _), hr in homerooms.items() if fn == old_form_num]
                        new_homeroom = random.choice(form_homerooms)
                else:
                    # Promote to next form
                    new_form = forms[old_form_num + 1]
                    # Pick random homeroom from new form
                    form_homerooms = [hr for (fn, _), hr in homerooms.items() if fn == old_form_num + 1]
                    new_homeroom = random.choice(form_homerooms)

                # Update student's current form and homeroom
                student.form = new_form
                student.homeroom = new_homeroom
                student.save()

                YearPlacement.objects.create(
                    student=student,
                    academic_year=year_2025,
                    form=new_form,
                    homeroom=new_homeroom,
                    outcome="continuing",
                    recorded_by=admin_user,
                )

                StudentStatusLog.objects.create(
                    student=student,
                    academic_year=year_2025,
                    status="enrolled",
                    change_date=year_2025.start_date,
                    reason="Promoted" if new_form.order > old_form_num else "Repeating",
                )

                students_2025.append(student)

        # Add new Form 1 students for 2025-2026
        for (form_num, homeroom_name), homeroom in homerooms.items():
            if form_num == 1:
                form = forms[form_num]
                num_new_students = random.randint(15, 20)

                for i in range(num_new_students):
                    gender = random.choice(["M", "F"])
                    first_names = DOMINICAN_FIRST_NAMES_MALE if gender == "M" else DOMINICAN_FIRST_NAMES_FEMALE
                    first_name = random.choice(first_names)
                    last_name = random.choice(DOMINICAN_LAST_NAMES)

                    student_id = f"{year_2025.name[:4]}-{form_num}{homeroom_name}-{i + 1:02d}"
                    email = f"{first_name.lower()}.{last_name.lower()}{i + 100:02d}@student.smadominica.com"

                    user, _ = User.objects.get_or_create(
                        email=email,
                        defaults={
                            "first_name": first_name,
                            "last_name": last_name,
                            "password": make_password("student123"),
                            "is_active": True,
                        },
                    )

                    UserRole.objects.get_or_create(
                        user=user,
                        school=school,
                        defaults={"role": "student"},
                    )

                    student, created = Student.objects.get_or_create(
                        school=school,
                        student_id=student_id,
                        defaults={
                            "first_name": first_name,
                            "last_name": last_name,
                            "form": form,
                            "homeroom": homeroom,
                            "gender": gender,
                            "date_of_birth": fake.date_of_birth(minimum_age=10, maximum_age=12),
                            "admission_date": year_2025.start_date,
                            "house": random.choice(houses),
                        },
                    )

                    if created:
                        StudentStatusLog.objects.create(
                            student=student,
                            academic_year=year_2025,
                            status="enrolled",
                            change_date=year_2025.start_date,
                            reason="New student",
                        )

                        YearPlacement.objects.create(
                            student=student,
                            academic_year=year_2025,
                            form=form,
                            homeroom=homeroom,
                            outcome="continuing",
                            recorded_by=admin_user,
                        )

                        students_2025.append(student)

        self.stdout.write(f"[+] Promoted/created {len(students_2025)} students for 2025-2026")
        return students_2025

    def create_sections(self, school, academic_year, forms, courses, teachers):
        """Create sections for all courses"""
        sections = {}
        teacher_list = list(teachers.values())

        for code, course in courses.items():
            # Extract form number from code
            form_num = None
            for char in code:
                if char.isdigit():
                    form_num = int(char)
                    break

            if form_num is None:
                continue

            form = forms[form_num]

            for term_num in [1, 2, 3]:
                section, created = Section.objects.get_or_create(
                    school=school,
                    course=course,
                    academic_year=academic_year,
                    term_number=term_num,
                    form=form,
                    defaults={
                        "teacher": random.choice(teacher_list),
                    },
                )
                sections[(code, form_num, term_num)] = section

        self.stdout.write(f"[+] Created {len(sections)} sections for {academic_year.name}")
        return sections

    def create_enrolments(self, school, academic_year, forms, students, sections):
        """Enroll students in all core courses for their form"""
        enrolments_created = 0

        for student in students:
            # Get student's placement for this year
            placement = YearPlacement.objects.filter(student=student, academic_year=academic_year).first()

            if not placement or placement.outcome != "continuing":
                continue

            form_num = placement.form.order

            # Enroll in all sections for their form
            for (code, section_form_num, term_num), section in sections.items():
                if section_form_num == form_num:
                    _, created = Enrolment.objects.get_or_create(
                        student=student,
                        section=section,
                        defaults={
                            "source": "homeroom",
                            "source_homeroom": placement.homeroom,
                        },
                    )
                    if created:
                        enrolments_created += 1

        self.stdout.write(f"[+] Created {enrolments_created} enrolments for {academic_year.name}")

    def create_timetables(self, school, academic_year, forms, sections, periods):
        """Create timetable structure and fill in slots"""
        timetables = {}
        for form in forms.values():
            for term_num in [1, 2, 3]:
                timetable, _ = Timetable.objects.get_or_create(
                    school=school,
                    form=form,
                    academic_year=academic_year,
                    term_number=term_num,
                )
                timetables[(form.order, term_num)] = timetable

        self.stdout.write(f"[+] Created timetables for {academic_year.name}")

        # Create timetable slots
        slots_created = self.create_timetable_slots(school, academic_year, forms, sections, timetables, periods)
        self.stdout.write(f"[+] Created {slots_created} timetable slots for {academic_year.name}")

    def create_timetable_slots(self, school, academic_year, forms, sections, timetables, periods):
        """Create timetable slots from schedule data

        Since we have comprehensive schedule data, we'll create sample slots by:
        1. Iterating through each form's timetable
        2. For each day (1-6) and period (1-7), randomly assign sections
        3. Ensure each section appears a reasonable number of times per week
        """
        slots_created = 0

        # For each form, create a reasonable timetable distribution
        for form_num in range(1, 6):
            form = forms[form_num]

            # Get all sections for this form (all 3 terms)
            for term_num in [1, 2, 3]:
                timetable = timetables.get((form_num, term_num))
                if not timetable:
                    continue

                # Get sections for this form and term
                form_sections = []
                for (code, section_form_num, section_term_num), section in sections.items():
                    if section_form_num == form_num and section_term_num == term_num:
                        form_sections.append(section)

                if not form_sections:
                    continue

                # Create a weekly schedule (6 days × 7 periods = 42 slots)
                # We'll assign ~6-8 sections per day (covering main subjects multiple times per week)
                periods_list = list(periods)

                # Core subjects that should appear more frequently
                core_codes = [
                    f"ENG{form_num}",
                    f"MAT{form_num}",
                    f"INT{form_num}",
                    f"SPA{form_num}",
                    f"FRE{form_num}",
                    f"HIS{form_num}",
                    f"REL{form_num}",
                    f"PE{form_num}",
                ]

                for day in range(1, 7):  # Days 1-6
                    # Shuffle sections for variety
                    daily_sections = random.sample(form_sections, min(len(form_sections), 7))

                    for period_idx, period in enumerate(periods_list[:7]):  # 7 periods
                        if period_idx < len(daily_sections):
                            section = daily_sections[period_idx]

                            _, created = TimetableSlot.objects.get_or_create(
                                timetable=timetable,
                                school=school,
                                day_number=day,
                                period=period,
                                section=section,
                            )
                            if created:
                                slots_created += 1

        return slots_created

    def create_grade_windows(self, school, academic_year, forms):
        """Create grade windows for all forms and terms"""
        for form in forms.values():
            for term_num in [1, 2, 3]:
                # Current year (2025-2026) Term 3 should be open
                is_open = academic_year.is_current and term_num == 3

                GradeWindow.objects.get_or_create(
                    school=school,
                    academic_year=academic_year,
                    term_number=term_num,
                    form=form,
                    defaults={"is_open": is_open},
                )

        self.stdout.write(f"[+] Created grade windows for {academic_year.name}")

    def create_evaluations_and_grades(self, school, academic_year, sections, terms=None):
        """Create evaluations and grade entries"""
        if terms is None:
            terms = [1, 2, 3]

        evaluations_created = 0
        grades_created = 0

        for (code, form_num, term_num), section in sections.items():
            if term_num not in terms:
                continue

            # Get term config to check if it has exam
            term_config = TermConfig.objects.get(academic_year=academic_year, term_number=term_num)

            # Get students enrolled in this section
            enrolments = Enrolment.objects.filter(section=section)

            # Create coursework evaluation
            cw_eval, created = Evaluation.objects.get_or_create(
                school=school,
                section=section,
                title=f"Coursework",
                category="coursework",
                subcategory="assignment",
                defaults={
                    "max_marks": Decimal(term_config.coursework_weight),
                    "weight": Decimal("1.00"),
                    "is_final_exam": False,
                    "date": term_config.start_date + timedelta(days=30),
                },
            )
            if created:
                evaluations_created += 1

            # Create grades for coursework
            for enrolment in enrolments:
                marks = random.randint(int(term_config.coursework_weight * 0.4), int(term_config.coursework_weight))
                _, created = GradeEntry.objects.get_or_create(
                    school=school,
                    evaluation=cw_eval,
                    student=enrolment.student,
                    defaults={
                        "marks_earned": Decimal(marks),
                        "is_absent": False,
                    },
                )
                if created:
                    grades_created += 1

            # Create exam evaluation if term has exam
            if term_config.has_final_exam:
                exam_eval, created = Evaluation.objects.get_or_create(
                    school=school,
                    section=section,
                    title=f"Final Exam",
                    category="exam",
                    subcategory="final_exam",
                    defaults={
                        "max_marks": Decimal(term_config.exam_weight),
                        "weight": Decimal("1.00"),
                        "is_final_exam": True,
                        "date": term_config.end_date - timedelta(days=5),
                    },
                )
                if created:
                    evaluations_created += 1

                # Create grades for exam
                for enrolment in enrolments:
                    marks = random.randint(int(term_config.exam_weight * 0.3), int(term_config.exam_weight))
                    _, created = GradeEntry.objects.get_or_create(
                        school=school,
                        evaluation=exam_eval,
                        student=enrolment.student,
                        defaults={
                            "marks_earned": Decimal(marks),
                            "is_absent": random.random() < 0.02,  # 2% absent
                        },
                    )
                    if created:
                        grades_created += 1

        self.stdout.write(f"[+] Created {evaluations_created} evaluations and {grades_created} grades for {academic_year.name}")

    def create_attendance(self, school, academic_year, students):
        """Create attendance records for first 2 months"""
        start_date = academic_year.start_date
        end_date = start_date + timedelta(days=60)
        attendance_created = 0

        current = start_date
        while current <= end_date:
            if current.weekday() < 5:  # Monday to Friday
                for student in students[:50]:  # Only first 50 students to save time
                    placement = YearPlacement.objects.filter(student=student, academic_year=academic_year).first()

                    if not placement or placement.outcome != "continuing":
                        continue

                    status_weights = [
                        ("present", 0.85),
                        ("absent", 0.05),
                        ("late", 0.08),
                        ("excused", 0.02),
                    ]
                    status = random.choices([s[0] for s in status_weights], weights=[s[1] for s in status_weights])[0]

                    _, created = Attendance.objects.get_or_create(
                        student=student,
                        academic_year=academic_year,
                        date=current,
                        defaults={
                            "school": school,
                            "homeroom": placement.homeroom,
                            "status": status,
                        },
                    )
                    if created:
                        attendance_created += 1

            current += timedelta(days=1)

        self.stdout.write(f"[+] Created {attendance_created} attendance records for {academic_year.name}")

    def create_merits_and_demerits(self, school, academic_year, students, teachers):
        """Create merit and demerit records"""
        merits_created = 0
        demerits_created = 0
        teacher_list = list(teachers.values())

        start_date = academic_year.start_date
        end_date = start_date + timedelta(days=60)

        merit_reasons = [
            "Excellent class participation",
            "Outstanding test performance",
            "Helping other students",
            "Perfect attendance",
            "Exceptional project work",
        ]

        demerit_reasons = [
            "Late to class",
            "Missing homework",
            "Disruptive behavior",
            "Incomplete assignment",
            "Dress code violation",
        ]

        # 30% of students get merits
        for student in random.sample(students, int(len(students) * 0.3)):
            num_merits = random.randint(1, 3)
            for _ in range(num_merits):
                date = start_date + timedelta(days=random.randint(0, 60))
                _, created = MeritRecord.objects.get_or_create(
                    student=student,
                    school=school,
                    academic_year=academic_year,
                    date=date,
                    defaults={
                        "category": random.choice(["academic", "behaviour", "leadership"]),
                        "reason": random.choice(merit_reasons),
                        "count": random.randint(1, 2),
                        "awarded_by": random.choice(teacher_list),
                    },
                )
                if created:
                    merits_created += 1

        # 20% of students get demerits
        for student in random.sample(students, int(len(students) * 0.2)):
            num_demerits = random.randint(1, 2)
            for _ in range(num_demerits):
                date = start_date + timedelta(days=random.randint(0, 60))
                _, created = DemeritRecord.objects.get_or_create(
                    student=student,
                    school=school,
                    academic_year=academic_year,
                    date=date,
                    defaults={
                        "category": random.choice(["misconduct", "tardiness", "uniform"]),
                        "reason": random.choice(demerit_reasons),
                        "count": 1,
                        "awarded_by": random.choice(teacher_list),
                    },
                )
                if created:
                    demerits_created += 1

        self.stdout.write(f"[+] Created {merits_created} merits and {demerits_created} demerits for {academic_year.name}")

    def print_summary(self):
        self.stdout.write(self.style.SUCCESS("\n" + "=" * 80))
        self.stdout.write(self.style.SUCCESS("SEEDING COMPLETE!"))
        self.stdout.write(self.style.SUCCESS("=" * 80))
        self.stdout.write(self.style.SUCCESS(f"\nSchool: Saint Mary's Academy"))
        self.stdout.write(self.style.SUCCESS(f"Academic Years: 2024-2025 and 2025-2026"))
        self.stdout.write(self.style.SUCCESS(f"Forms: 5 (Form 1 to Form 5)"))
        self.stdout.write(self.style.SUCCESS(f"Homerooms: 15 total"))
        self.stdout.write(self.style.SUCCESS(f"  Form 1: 101, 102, 103"))
        self.stdout.write(self.style.SUCCESS(f"  Form 2: 104, 105, 201"))
        self.stdout.write(self.style.SUCCESS(f"  Form 3: 202, 203, wa5"))
        self.stdout.write(self.style.SUCCESS(f"  Form 4: 204, 205, 206"))
        self.stdout.write(self.style.SUCCESS(f"  Form 5: wa1, wa2, wa3"))
        self.stdout.write(self.style.SUCCESS(f"Teachers: {Staff.objects.count()}"))
        self.stdout.write(self.style.SUCCESS(f"Students: {Student.objects.count()}"))
        self.stdout.write(self.style.SUCCESS(f"Courses: {Course.objects.count()}"))
        self.stdout.write(self.style.SUCCESS(f"Sections: {Section.objects.count()}"))
        self.stdout.write(self.style.SUCCESS(f"Enrolments: {Enrolment.objects.count()}"))
        self.stdout.write(self.style.SUCCESS(f"\nTimetable: 6-day rotating cycle, 7 periods per day"))
        self.stdout.write(self.style.SUCCESS(f"Timetable Slots: {TimetableSlot.objects.count()}"))
        self.stdout.write(self.style.SUCCESS(f"\nGrade Windows: Term 3 of 2025-2026 is OPEN"))
        self.stdout.write(self.style.SUCCESS(f"\nLogin Credentials:"))
        self.stdout.write(self.style.SUCCESS(f"  Any teacher: <email>@smadominica.com | Password: teacher123"))
        self.stdout.write(self.style.SUCCESS(f"  Any student: <email>@student.smadominica.com | Password: student123"))
        self.stdout.write(self.style.SUCCESS(""))
