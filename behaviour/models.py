from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Q, F
from core.models import School
from students.models import Student
from scheduling.models import AcademicYear
from accounts.models import User


# Module-level choices
INCIDENT_TYPE_CHOICES = [
    ("detention", "Detention"),
    ("suspension", "Suspension"),
]

TERM_NUMBER_CHOICES = [
    (1, "Term 1"),
    (2, "Term 2"),
    (3, "Term 3"),
]

SUSPENSION_TYPE_CHOICES = [
    ("in_school", "In-School Suspension"),
    ("out_of_school", "Out-of-School Suspension"),
]


class BehaviourIncident(models.Model):
    # Core relations
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="behaviour_incidents")
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="behaviour_incidents")
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.PROTECT, related_name="behaviour_incidents")
    logged_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="behaviour_incidents_logged")

    # General incident fields
    incident_type = models.CharField(max_length=20, choices=INCIDENT_TYPE_CHOICES)
    incident_date = models.DateField(default=timezone.localdate)
    reason = models.TextField()
    term_number = models.PositiveSmallIntegerField(choices=TERM_NUMBER_CHOICES, null=True, blank=True)

    # Suspension-specific fields
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    suspension_type = models.CharField(max_length=20, choices=SUSPENSION_TYPE_CHOICES, null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "behaviour_incidents"
        ordering = ["-incident_date", "-created_at"]
        indexes = [
            models.Index(fields=["school", "incident_type"], name="behaviour_school_type_idx"),
            models.Index(fields=["school", "student"], name="behaviour_school_student_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(incident_type="detention")
                    | Q(
                        incident_type="suspension",
                        start_date__isnull=False,
                        end_date__isnull=False,
                        suspension_type__isnull=False,
                    )
                ),
                name="INCIDENT_TYPE_VALID",
            ),
        ]

    def __str__(self):
        return f"{self.student.get_full_name()} - {self.get_incident_type_display()} - {self.incident_date}"

    @property
    def is_detention(self):
        return self.incident_type == "detention"
        pass

    @property
    def is_suspension(self):
        return self.incident_type == "suspension"
        pass

    def clean(self):
        """Validate model fields according to incident type."""
        # Skip validation if school is not set (will be set by service layer)
        if not self.school_id:
            return

        # Ensure student belongs to this school
        if self.student and self.student.school != self.school:
            raise ValidationError("Student does not belong to this school.")

        if self.incident_type == "suspension":
            # Suspension-specific validation
            if not self.start_date:
                raise ValidationError({"start_date": "Start date is required for suspension incidents."})
            if not self.end_date:
                raise ValidationError({"end_date": "End date is required for suspension incidents."})
            if not self.suspension_type:
                raise ValidationError({"suspension_type": "Suspension type is required."})

            # Ensure end_date >= start_date
            if self.end_date < self.start_date:
                raise ValidationError({"end_date": "End date must be on or after the start date."})

            # Ensure start_date is not in the future
            if self.start_date > timezone.localtime().date():
                raise ValidationError({"start_date": "Suspension start date cannot be in the future."})

            # Check for overlapping suspensions with the same student
            overlapping = BehaviourIncident.objects.filter(
                school=self.school,
                student=self.student,
                incident_type="suspension",
                start_date__lte=self.end_date,
                end_date__gte=self.start_date,
            ).exclude(pk=self.pk)

            if overlapping.exists():
                raise ValidationError("This student already has an overlapping suspension in the database.")
        pass
