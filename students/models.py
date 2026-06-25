from django.db import models
from core.models import School
from accounts.models import User


class House(models.Model):
	school  = models.ForeignKey(School, on_delete=models.CASCADE, related_name="houses")
	name    = models.CharField(max_length=50)
	color   = models.CharField(max_length=7, blank=True)  # hex color for UI

	class Meta:
		db_table        = "houses"
		ordering        = ["name"]
		unique_together = ("school", "name")

	def __str__(self):
		return self.name
	
	
class Student(models.Model):

	GENDER_CHOICES = [
		("M", "Male"),
		("F", "Female"),
		("O", "Other"),
	]

	STATUS_CHOICES = [
		("enrolled",    "Enrolled"),
		("withdrawn",   "Withdrawn"),
		("suspended",   "Suspended"),
		("graduated",   "Graduated"),
		("transferred", "Transferred"),
		("on_leave",    "On Leave"),
	]

	RELIGION_CHOICES = [
		("roman_catholic",  "Roman Catholic"),
		("anglican",        "Anglican"),
		("seventh_day",     "Seventh Day Adventist"),
		("pentecostal",     "Pentecostal"),
		("methodist",       "Methodist"),
		("baptist",         "Baptist"),
		("jehovah",         "Jehovah's Witness"),
		("muslim",          "Muslim"),
		("hindu",           "Hindu"),
		("other",           "Other"),
		("none",            "None"),
	]

	LIVES_WITH_CHOICES = [
		("both_parents",  "Both Parents"),
		("mother",        "Mother"),
		("father",        "Father"),
		("guardian",      "Guardian"),
		("other",         "Other"),
	]

	GSNA_CHOICES = [
		("",    "—"),
		("1",   "Grade 1"),
		("2",   "Grade 2"),
		("3",   "Grade 3"),
		("4",   "Grade 4"),
		("5",   "Grade 5"),
		("6",   "Grade 6"),
	]

	# Core identity
	school          = models.ForeignKey(School, on_delete=models.CASCADE, related_name="students")
	user            = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="student_profile")
	student_id      = models.CharField(max_length=50)
	first_name      = models.CharField(max_length=100)
	middle_name     = models.CharField(max_length=100, blank=True)
	last_name       = models.CharField(max_length=100)
	gender          = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
	date_of_birth   = models.DateField(null=True, blank=True)
	nationality     = models.CharField(max_length=100, blank=True)
	religion        = models.CharField(max_length=30, choices=RELIGION_CHOICES, blank=True)
	house           = models.ForeignKey(House, on_delete=models.SET_NULL, null=True, blank=True, related_name="students")

	# Contact
	phone           = models.CharField(max_length=30, blank=True)
	email           = models.EmailField(blank=True)
	address         = models.TextField(blank=True)
	city            = models.CharField(max_length=100, blank=True)
	parish          = models.CharField(max_length=100, blank=True)
	community       = models.CharField(max_length=100, blank=True)

	# Academic placement
	form            = models.ForeignKey("scheduling.Form", on_delete=models.SET_NULL, null=True, blank=True, related_name="students")
	homeroom        = models.ForeignKey("scheduling.Homeroom", on_delete=models.SET_NULL, null=True, blank=True, related_name="students")
	admission_date  = models.DateField(null=True, blank=True)
	previous_school = models.CharField(max_length=200, blank=True)

	# Photo
	photo           = models.ImageField(upload_to="students/photos/", blank=True, null=True)

	# Official IDs
	emis_id         = models.CharField(max_length=50, blank=True)
	csec_candidate_no = models.CharField(max_length=50, blank=True)

	# Cohort / repeat tracking
	cohort_grade    = models.CharField(max_length=20, blank=True)
	cohort_year     = models.CharField(max_length=10, blank=True)
	repeated        = models.CharField(max_length=100, blank=True)

	# GSNA
	gsna_year       = models.CharField(max_length=10, blank=True)
	gsna_award      = models.CharField(max_length=50, blank=True)
	gsna_english    = models.CharField(max_length=1, choices=GSNA_CHOICES, blank=True)
	gsna_mathematics = models.CharField(max_length=1, choices=GSNA_CHOICES, blank=True)
	gsna_science    = models.CharField(max_length=1, choices=GSNA_CHOICES, blank=True)
	gsna_social_studies = models.CharField(max_length=1, choices=GSNA_CHOICES, blank=True)

	# Graduation / sponsor
	grad_date       = models.DateField(null=True, blank=True)
	sponsor         = models.CharField(max_length=200, blank=True)

	# Legal/birth parents (simple fields)
	father_name     = models.CharField(max_length=200, blank=True)
	mother_name     = models.CharField(max_length=200, blank=True)

	# Emergency contact
	emergency_contact_name      = models.CharField(max_length=200, blank=True)
	emergency_relation          = models.CharField(max_length=100, blank=True)
	emergency_phone_1           = models.CharField(max_length=30, blank=True)
	emergency_phone_2           = models.CharField(max_length=30, blank=True)
	emergency_work_phone        = models.CharField(max_length=30, blank=True)
	emergency_workplace         = models.CharField(max_length=200, blank=True)

	# Doctor
	doctor_name     = models.CharField(max_length=200, blank=True)
	doctor_phone    = models.CharField(max_length=30, blank=True)

	# Contact restrictions
	restrict_contact_1 = models.CharField(max_length=200, blank=True)
	restrict_contact_2 = models.CharField(max_length=200, blank=True)
	lives_with      = models.CharField(max_length=20, choices=LIVES_WITH_CHOICES, blank=True)

	# Notes
	notes           = models.TextField(blank=True)

	created_at      = models.DateTimeField(auto_now_add=True)
	updated_at      = models.DateTimeField(auto_now=True)

	class Meta:
		db_table        = "students"
		ordering        = ["last_name", "first_name"]
		unique_together = ("school", "student_id")

	def __str__(self):
		return f"{self.first_name} {self.last_name} ({self.student_id})"

	def get_full_name(self):
		if self.middle_name:
			return f"{self.first_name} {self.middle_name} {self.last_name}"
		return f"{self.first_name} {self.last_name}"

	def current_status(self):
		log = self.status_logs.order_by("-change_date").first()
		return log.status if log else "enrolled"

	def current_status_display(self):
		status = self.current_status()
		return dict(self.STATUS_CHOICES).get(status, status)


class Guardian(models.Model):

	RELATIONSHIP_CHOICES = [
		("mother",  "Mother"),
		("father",  "Father"),
		("sibling", "Sibling"),
		("uncle",   "Uncle"),
		("aunt",    "Aunt"),
		("grandparent", "Grandparent"),
		("other",   "Other"),
	]

	school          = models.ForeignKey(School, on_delete=models.CASCADE, related_name="guardians")
	first_name      = models.CharField(max_length=100)
	last_name       = models.CharField(max_length=100)
	phone           = models.CharField(max_length=30, blank=True)
	email           = models.EmailField(blank=True)
	address         = models.TextField(blank=True)
	created_at      = models.DateTimeField(auto_now_add=True)

	class Meta:
		db_table = "guardians"
		ordering = ["last_name", "first_name"]

	def __str__(self):
		return f"{self.first_name} {self.last_name}"

	def get_full_name(self):
		return f"{self.first_name} {self.last_name}"


class StudentGuardian(models.Model):

	student         = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="guardians")
	guardian        = models.ForeignKey(Guardian, on_delete=models.CASCADE, related_name="students")
	relationship    = models.CharField(max_length=20, choices=Guardian.RELATIONSHIP_CHOICES)
	is_primary      = models.BooleanField(default=False)
	can_pickup      = models.BooleanField(default=True)

	class Meta:
		db_table        = "student_guardians"
		unique_together = ("student", "guardian")

	def __str__(self):
		return f"{self.guardian} → {self.student} ({self.relationship})"


class StudentStatusLog(models.Model):

	STATUS_CHOICES = Student.STATUS_CHOICES

	student     = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="status_logs")
	status      = models.CharField(max_length=20, choices=STATUS_CHOICES)
	change_date = models.DateField()
	reason      = models.CharField(max_length=200, blank=True)   # short reason/category
	description = models.TextField(blank=True)                    # longer notes
	changed_by  = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="status_changes")
	created_at  = models.DateTimeField(auto_now_add=True)

	class Meta:
		db_table = "student_status_logs"
		ordering = ["-change_date"]

	def __str__(self):
		return f"{self.student} → {self.status} on {self.change_date}"

class StudentNote(models.Model):
	"""Staff-only notes thread on a student. Visible to teachers + admins only."""

	school     = models.ForeignKey(School, on_delete=models.CASCADE, related_name="student_notes")
	student    = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="staff_notes")
	body       = models.TextField()
	author     = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="student_notes_authored")
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		db_table = "student_notes"
		ordering = ["-created_at"]

	def __str__(self):
		return f"Note on {self.student} by {self.author}"
		pass
	pass