from django.core.exceptions import ValidationError
from django.db import models
from core.models import School


class Form(models.Model):
    """Year group / grade level e.g. Form 1, Form 2"""

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="forms")
    name = models.CharField(max_length=50)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "forms"
        ordering = ["order", "name"]
        unique_together = ("school", "name")

    def __str__(self):
        return self.name


class Homeroom(models.Model):
    """A class/homeroom group within a form"""

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="homerooms")
    form = models.ForeignKey(Form, on_delete=models.CASCADE, related_name="homerooms")
    name = models.CharField(max_length=50)

    class Meta:
        db_table = "homerooms"
        ordering = ["form", "name"]
        unique_together = ("school", "name")

    def __str__(self):
        return f"{self.form.name} — {self.name}"


class AcademicYear(models.Model):
    """e.g. 2024-2025"""

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="academic_years")
    name = models.CharField(max_length=20)  # e.g. "2024-2025"
    is_current = models.BooleanField(default=False)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "academic_years"
        ordering = ["-name"]
        unique_together = ("school", "name")

    def __str__(self):
        return f"{self.name} ({'Current' if self.is_current else 'Inactive'})"

    def save(self, *args, **kwargs):
        # Only one current year per school
        if self.is_current:
            AcademicYear.objects.filter(school=self.school, is_current=True).exclude(pk=self.pk).update(is_current=False)
        super().save(*args, **kwargs)


class TermConfig(models.Model):
    """Defines structure of each term within an academic year"""

    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name="term_configs")
    term_number = models.PositiveIntegerField()  # 1, 2, 3
    name = models.CharField(max_length=50)  # e.g. "Term 1"
    has_final_exam = models.BooleanField(default=True)
    coursework_weight = models.PositiveIntegerField(default=60)  # %
    exam_weight = models.PositiveIntegerField(default=40)  # %
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "term_configs"
        ordering = ["term_number"]
        unique_together = ("academic_year", "term_number")

    def __str__(self):
        return f"{self.academic_year.name} — {self.name}"

    def clean(self):
        if self.has_final_exam:
            if self.coursework_weight + self.exam_weight != 100:
                raise ValidationError("Coursework weight and exam weight must add up to 100.")
        else:
            self.exam_weight = 0
            self.coursework_weight = 100

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class FormTermRule(models.Model):
    """
    Per-form overrides for a specific term.
    e.g. Form 5, Term 3 → exam_label='Mock Exam', exam_replaces_final=True
    """

    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name="form_term_rules")
    form = models.ForeignKey(Form, on_delete=models.CASCADE, related_name="term_rules")
    term_number = models.PositiveIntegerField()
    exam_label = models.CharField(max_length=100, default="Final Exam")
    exam_replaces_final = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "form_term_rules"
        unique_together = ("academic_year", "form", "term_number")

    def __str__(self):
        return f"{self.form} — Term {self.term_number} — {self.exam_label}"


class NonSchoolDay(models.Model):
    TYPE_CHOICES = [
        ("holiday", "Public Holiday"),
        ("impromptu", "Impromptu Closure"),
        ("event", "School Event"),
    ]

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="non_school_days")
    date = models.DateField()
    label = models.CharField(max_length=100)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    created_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True)

    class Meta:
        db_table = "non_school_days"
        ordering = ["date"]
        unique_together = ("school", "date")

    def __str__(self):
        return f"{self.label} ({self.date})"


class Course(models.Model):
    INSTRUCTIONAL_MODE_CHOICES = [
        ("lecture", "Lecture"),
        ("lab", "Laboratory"),
        ("online", "Online"),
        ("hybrid", "Hybrid"),
        ("practical", "Practical"),
        ("other", "Other"),
    ]

    SUBJECT_AREA_CHOICES = [
        ("mathematics", "Mathematics"),
        ("sciences", "Sciences"),
        ("languages", "Languages"),
        ("social_studies", "Social Studies"),
        ("technology", "Technology"),
        ("arts", "Arts"),
        ("physical_ed", "Physical Education"),
        ("other", "Other"),
    ]

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="courses")
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, blank=True)
    short_description = models.CharField(max_length=8, blank=True)
    description = models.TextField(blank=True)
    section_number = models.CharField(max_length=10, default="1", blank=True)
    form = models.ForeignKey("Form", on_delete=models.SET_NULL, null=True, blank=True, related_name="course_masters")
    start_term = models.PositiveIntegerField(null=True, blank=True)
    end_term = models.PositiveIntegerField(null=True, blank=True)
    teacher = models.ForeignKey("staff.Staff", on_delete=models.SET_NULL, null=True, blank=True, related_name="primary_courses")
    teacher_2 = models.ForeignKey("staff.Staff", on_delete=models.SET_NULL, null=True, blank=True, related_name="secondary_courses")
    sequence = models.PositiveIntegerField(default=100)
    web_visible = models.BooleanField(default=True)
    instructional_mode = models.CharField(max_length=20, choices=INSTRUCTIONAL_MODE_CHOICES, blank=True)
    faculty = models.CharField(max_length=100, blank=True)
    room = models.CharField(max_length=50, blank=True)
    subject_area = models.CharField(max_length=30, choices=SUBJECT_AREA_CHOICES, blank=True)
    calc_average = models.BooleanField(default=True)
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "courses"
        ordering = ["sequence", "name"]
        unique_together = ("school", "name")

    def __str__(self):
        return f"{self.code} — {self.name}" if self.code else self.name


class Section(models.Model):
    """
    A specific class offering of a Course in a Term for a Form.
    This is the pivot — grades, attendance, enrolments all attach here.
    """

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="sections")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="sections")
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name="sections")
    term_number = models.PositiveIntegerField()
    form = models.ForeignKey(Form, on_delete=models.CASCADE, related_name="sections")
    teacher = models.ForeignKey("staff.Staff", on_delete=models.SET_NULL, null=True, blank=True, related_name="sections")
    room = models.CharField(max_length=50, blank=True)

    class Meta:
        db_table = "sections"
        ordering = ["academic_year", "term_number", "course"]

    def __str__(self):
        return f"{self.course} — {self.form} — Term {self.term_number} ({self.academic_year})"


class Enrolment(models.Model):
    """Links a Student to a Section"""

    SOURCE_CHOICES = [
        ("manual", "Individual"),
        ("homeroom", "Homeroom"),
    ]

    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="enrolments")
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="enrolments")
    date_enrolled = models.DateField(auto_now_add=True)
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default="manual")
    source_homeroom = models.ForeignKey(
        "scheduling.Homeroom",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sourced_enrolments",
    )

    class Meta:
        db_table = "enrolments"
        unique_together = ("student", "section")

    def __str__(self):
        return f"{self.student} → {self.section}"


# Timetable models

CYCLE = "cycle"
WEEKDAY = "weekday"


class TimetableSettings(models.Model):
    MODE_CHOICES = [
        (CYCLE, "Rotating day cycle (Day 1 … Day N)"),
        (WEEKDAY, "Regular weekly (Mon – Fri)"),
    ]
    school = models.OneToOneField("core.School", on_delete=models.CASCADE, related_name="timetable_settings")
    mode = models.CharField(max_length=10, choices=MODE_CHOICES, default=WEEKDAY)
    cycle_length = models.PositiveSmallIntegerField(default=6)
    anchor_date = models.DateField(
        null=True, blank=True, help_text="The first school day on/after this date is Day 1. Usually the first day of the academic year."
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Timetable settings — {self.school}"
        pass

    @property
    def is_cycle(self):
        return self.mode == CYCLE
        pass


class TimetablePeriod(models.Model):
    """The bell schedule — shared across every day and every form."""

    school = models.ForeignKey("core.School", on_delete=models.CASCADE, related_name="timetable_periods")
    name = models.CharField(max_length=50)  # "Period 1", "Lunch"
    order = models.PositiveSmallIntegerField(default=1)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    is_break = models.BooleanField(default=False, help_text="Recess, lunch, assembly — no class scheduled.")

    class Meta:
        ordering = ["order"]
        unique_together = ("school", "order")

    def __str__(self):
        return self.name
        pass


class Timetable(models.Model):
    """One form's timetable for one term. This is the 'page' you open and edit."""

    school = models.ForeignKey("core.School", on_delete=models.CASCADE, related_name="timetables")
    form = models.ForeignKey("scheduling.Form", on_delete=models.CASCADE, related_name="timetables")
    academic_year = models.ForeignKey("scheduling.AcademicYear", on_delete=models.CASCADE, related_name="timetables")
    term_number = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("school", "form", "academic_year", "term_number")
        ordering = ["form", "academic_year", "term_number"]

    def __str__(self):
        return f"{self.form} — {self.academic_year} Term {self.term_number}"
        pass


class TimetableSlot(models.Model):
    """One section placed in a (day, period) cell of a form's term timetable.
    Multiple slots may share the same (timetable, day, period) cell — that is a
    switch/split period (e.g. French 101 + Spanish 101 in the same slot)."""

    timetable = models.ForeignKey(Timetable, on_delete=models.CASCADE, related_name="slots")
    school = models.ForeignKey("core.School", on_delete=models.CASCADE, related_name="timetable_slots")
    day_number = models.PositiveSmallIntegerField(help_text="Cycle mode: 1..N = Day 1..Day N. Weekly mode: 1=Mon … 5=Fri.")
    period = models.ForeignKey(TimetablePeriod, on_delete=models.CASCADE, related_name="slots")
    section = models.ForeignKey("scheduling.Section", on_delete=models.CASCADE, related_name="timetable_slots")

    class Meta:
        # Same section can't be placed twice in one cell, but several different
        # sections CAN share a cell — that is the split/switch class.
        unique_together = ("timetable", "day_number", "period", "section")
        ordering = ["day_number", "period__order"]

    def __str__(self):
        return f"Day {self.day_number} / {self.period} → {self.section}"
        pass
