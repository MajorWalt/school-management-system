from django.db import models
from django.core.exceptions import ValidationError
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