import math
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from core.models import School
from accounts.models import User


class Staff(models.Model):
    GENDER_CHOICES = [
        ("M", "Male"),
        ("F", "Female"),
        ("O", "Other"),
    ]

    SALUTATION_CHOICES = [
        ("Mr", "Mr"),
        ("Mrs", "Mrs"),
        ("Ms", "Ms"),
        ("Dr", "Dr"),
        ("Rev", "Rev"),
        ("Hon", "Hon"),
    ]

    TEACHER_STATUS_CHOICES = [
        ("trained", "Trained Teacher"),
        ("untrained", "Untrained Teacher"),
        ("temporary", "Temporary"),
        ("substitute", "Substitute"),
        ("administrator", "Administrator"),
        ("support", "Support Staff"),
        ("other", "Other"),
    ]

    DEGREE_CHOICES = [
        ("none", "None"),
        ("certificate", "Certificate"),
        ("associate", "Associate Degree"),
        ("bachelor", "Bachelor's Degree"),
        ("postgrad", "Post-Graduate Certificate"),
        ("master", "Master's Degree"),
        ("doctorate", "Doctorate / PhD"),
        ("other", "Other"),
    ]

    RELATION_CHOICES = [
        ("spouse", "Spouse"),
        ("parent", "Parent"),
        ("sibling", "Sibling"),
        ("child", "Child"),
        ("friend", "Friend"),
        ("other", "Other"),
    ]

    DEPARTMENT_CHOICES = [
        ("Mathematics", "Mathematics"),
        ("English", "English / Language Arts"),
        ("Natural Sciences", "Natural Sciences"),
        ("Social Studies", "Social Studies"),
        ("Modern Languages", "Modern Languages"),
        ("Information Technology", "Information Technology"),
        ("Business Studies", "Business Studies"),
        ("Physical Education", "Physical Education"),
        ("Visual & Performing Arts", "Visual & Performing Arts"),
        ("Technical", "Technical"),
        ("Religious Education", "Religious Education"),
        ("Building & Tech Draw", "Building & Technical Drawing"),
        ("Geography", "Geography"),
        ("History", "History"),
        ("Agriculture", "Agriculture"),
    ]

    # Core identity
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="staff")
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="staff_profile")
    employee_number = models.CharField(max_length=50, unique=True)
    salutation = models.CharField(max_length=10, choices=SALUTATION_CHOICES, blank=True)
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    nationality = models.CharField(max_length=100, blank=True)
    social_security_no = models.CharField(max_length=50, blank=True)
    house = models.CharField(max_length=100, blank=True)
    emis_id = models.CharField(max_length=50, blank=True)

    # Contact
    phone_1 = models.CharField(max_length=30, blank=True)
    phone_2 = models.CharField(max_length=30, blank=True)
    phone_3 = models.CharField(max_length=30, blank=True)
    email_work = models.EmailField(blank=True)
    email_personal = models.EmailField(blank=True)
    email_emis = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    parish = models.CharField(max_length=100, blank=True)

    # Employment
    department = models.CharField(max_length=100, choices=DEPARTMENT_CHOICES, blank=True)
    department_2 = models.CharField("Second department", max_length=100, choices=DEPARTMENT_CHOICES, blank=True)
    is_head_of_department = models.BooleanField("Head of Department", default=False)
    role_title = models.CharField(max_length=100, blank=True)
    subject_specialisation = models.CharField(max_length=100, blank=True)
    hire_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    does_attendance = models.BooleanField(default=True)
    active = models.BooleanField(default=True)
    homeroom = models.ForeignKey("scheduling.Homeroom", on_delete=models.SET_NULL, null=True, blank=True, related_name="staff_members")

    # Emergency contact
    emergency_contact_name = models.CharField(max_length=200, blank=True)
    emergency_contact_phone = models.CharField(max_length=30, blank=True)
    emergency_contact_relation = models.CharField(max_length=20, choices=RELATION_CHOICES, blank=True)

    # MoE Teaching & Qualification
    teacher_type = models.CharField(max_length=20, choices=TEACHER_STATUS_CHOICES, blank=True)
    date_started_teaching = models.DateField(null=True, blank=True)
    date_appointed = models.DateField(null=True, blank=True)
    previous_schools = models.TextField(blank=True)
    highest_degree = models.CharField(max_length=20, choices=DEGREE_CHOICES, blank=True)
    degree_specification = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "staff"
        ordering = ["last_name", "first_name"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(is_head_of_department=False) | ~models.Q(department=""),
                name="hod_requires_department",
            ),
            models.CheckConstraint(
                condition=models.Q(department_2="") | ~models.Q(department=""),
                name="second_department_requires_first",
            ),
        ]

    def __str__(self):
        return f"{self.get_full_name()} ({self.employee_number})"
        pass

    def clean(self):
        super().clean()
        if self.department_2 and not self.department:
            raise ValidationError({"department_2": "Select a primary department before adding a second one."})
        if self.department and self.department_2 and self.department == self.department_2:
            raise ValidationError({"department_2": "The second department must be different from the first."})
        if self.is_head_of_department and not self.department:
            raise ValidationError({"is_head_of_department": "A staff member cannot be Head of Department without a department."})
        pass

    def get_full_name(self):
        parts = [self.salutation, self.first_name, self.middle_name, self.last_name]
        return " ".join(p for p in parts if p)
        pass

    def get_display_name(self):
        return f"{self.first_name} {self.last_name}"
        pass

    def get_departments(self):
        return [d for d in [self.department, self.department_2] if d]
        pass


class StaffClockIn(models.Model):
    STATUS_CHOICES = [
        ("present", "Present"),
        ("sick", "Sick"),
        ("excused", "Excused"),
    ]

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="staff_clock_ins")
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name="clock_ins")
    date = models.DateField()
    clock_in_time = models.TimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    note = models.TextField(blank=True)
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="recorded_clock_ins")

    # Location tracking
    latitude = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True, help_text="Clock-in latitude")
    longitude = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True, help_text="Clock-in longitude")
    distance_from_school = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="Distance in meters")
    within_radius = models.BooleanField(null=True, blank=True, help_text="Whether clock-in was within acceptable radius")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "staff_clock_in"
        ordering = ["-date", "-clock_in_time"]
        constraints = [
            models.UniqueConstraint(fields=["school", "staff", "date"], name="unique_staff_clockin_per_day"),
            models.CheckConstraint(
                condition=(models.Q(status="present", clock_in_time__isnull=False) | models.Q(status__in=["sick", "excused"], clock_in_time__isnull=True)),
                name="clockin_status_time_consistency",
            ),
        ]

    def __str__(self):
        return f"{self.staff.get_display_name()} - {self.date} ({self.get_status_display()})"
        pass

    def calculate_distance_and_status(self):
        """Calculate distance from school and set within_radius status."""
        if not self.latitude or not self.longitude:
            self.distance_from_school = None
            self.within_radius = None
            return
            pass

        if not self.school.latitude or not self.school.longitude:
            self.distance_from_school = None
            self.within_radius = None
            return
            pass

        # Haversine formula to calculate distance between two points on Earth
        R = 6371000  # Earth radius in meters

        lat1 = math.radians(float(self.school.latitude))
        lat2 = math.radians(float(self.latitude))
        delta_lat = math.radians(float(self.latitude) - float(self.school.latitude))
        delta_lon = math.radians(float(self.longitude) - float(self.school.longitude))

        a = math.sin(delta_lat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        distance = R * c  # Distance in meters
        self.distance_from_school = round(distance, 2)
        self.within_radius = distance <= self.school.location_radius_meters
        pass

    def clean(self):
        super().clean()

        # Staff school must equal self.school
        if self.staff and self.staff.school_id != self.school_id:
            raise ValidationError({"staff": "Staff member must belong to the same school."})
            pass

        # Date not in the future
        today = timezone.localtime().date()
        if self.date and self.date > today:
            raise ValidationError({"date": "Clock-in date cannot be in the future."})
            pass

        # Status="present" requires clock_in_time NOT NULL
        if self.status == "present" and not self.clock_in_time:
            raise ValidationError({"clock_in_time": "Clock-in time is required when status is Present."})
            pass

        # Status in (sick, excused) requires clock_in_time NULL
        if self.status in ("sick", "excused") and self.clock_in_time:
            raise ValidationError({"clock_in_time": "Clock-in time must be empty when status is Sick or Excused."})
            pass
        pass
