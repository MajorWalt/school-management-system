from django.db import models
from core.models import School
from accounts.models import User


class Staff(models.Model):

	GENDER_CHOICES = [
		("M", "Male"),
		("F", "Female"),
		("O", "Other"),
	]

	SALUTATION_CHOICES = [
		("Mr",  "Mr"),
		("Mrs", "Mrs"),
		("Ms",  "Ms"),
		("Dr",  "Dr"),
		("Rev", "Rev"),
		("Hon", "Hon"),
	]

	TEACHER_STATUS_CHOICES = [
		("trained",       "Trained Teacher"),
		("untrained",     "Untrained Teacher"),
		("temporary",     "Temporary"),
		("substitute",    "Substitute"),
		("administrator", "Administrator"),
		("support",       "Support Staff"),
		("other",         "Other"),
	]

	DEGREE_CHOICES = [
		("none",        "None"),
		("certificate", "Certificate"),
		("associate",   "Associate Degree"),
		("bachelor",    "Bachelor's Degree"),
		("postgrad",    "Post-Graduate Certificate"),
		("master",      "Master's Degree"),
		("doctorate",   "Doctorate / PhD"),
		("other",       "Other"),
	]

	RELATION_CHOICES = [
		("spouse",    "Spouse"),
		("parent",    "Parent"),
		("sibling",   "Sibling"),
		("child",     "Child"),
		("friend",    "Friend"),
		("other",     "Other"),
	]

	# Core identity
	school              = models.ForeignKey(School, on_delete=models.CASCADE, related_name="staff")
	user                = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="staff_profile")
	employee_number     = models.CharField(max_length=50, unique=True)
	salutation          = models.CharField(max_length=10, choices=SALUTATION_CHOICES, blank=True)
	first_name          = models.CharField(max_length=100)
	middle_name         = models.CharField(max_length=100, blank=True)
	last_name           = models.CharField(max_length=100)
	gender              = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
	date_of_birth       = models.DateField(null=True, blank=True)
	nationality         = models.CharField(max_length=100, blank=True)
	social_security_no  = models.CharField(max_length=50, blank=True)
	house               = models.CharField(max_length=100, blank=True)
	emis_id             = models.CharField(max_length=50, blank=True)

	# Contact
	phone_1             = models.CharField(max_length=30, blank=True)
	phone_2             = models.CharField(max_length=30, blank=True)
	phone_3             = models.CharField(max_length=30, blank=True)
	email_work          = models.EmailField(blank=True)
	email_personal      = models.EmailField(blank=True)
	email_emis          = models.EmailField(blank=True)
	address             = models.TextField(blank=True)
	city                = models.CharField(max_length=100, blank=True)
	parish              = models.CharField(max_length=100, blank=True)

	# Employment
	department          = models.CharField(max_length=100, blank=True)
	role_title          = models.CharField(max_length=100, blank=True)
	subject_specialisation = models.CharField(max_length=100, blank=True)
	hire_date           = models.DateField(null=True, blank=True)
	end_date            = models.DateField(null=True, blank=True)
	does_attendance     = models.BooleanField(default=True)
	active              = models.BooleanField(default=True)
	homeroom            = models.ForeignKey(
		"scheduling.Homeroom", on_delete=models.SET_NULL,
		null=True, blank=True, related_name="staff_members"
	)

	# Emergency contact
	emergency_contact_name      = models.CharField(max_length=200, blank=True)
	emergency_contact_phone     = models.CharField(max_length=30, blank=True)
	emergency_contact_relation  = models.CharField(max_length=20, choices=RELATION_CHOICES, blank=True)

	# MoE Teaching & Qualification
	teacher_type        = models.CharField(max_length=20, choices=TEACHER_STATUS_CHOICES, blank=True)
	date_started_teaching = models.DateField(null=True, blank=True)
	date_appointed      = models.DateField(null=True, blank=True)
	previous_schools    = models.TextField(blank=True)
	highest_degree      = models.CharField(max_length=20, choices=DEGREE_CHOICES, blank=True)
	degree_specification = models.TextField(blank=True)

	created_at          = models.DateTimeField(auto_now_add=True)
	updated_at          = models.DateTimeField(auto_now=True)

	class Meta:
		db_table = "staff"
		ordering = ["last_name", "first_name"]

	def __str__(self):
		return f"{self.get_full_name()} ({self.employee_number})"

	def get_full_name(self):
		parts = [self.salutation, self.first_name, self.middle_name, self.last_name]
		return " ".join(p for p in parts if p)

	def get_display_name(self):
		return f"{self.first_name} {self.last_name}"