from django.db import models
from core.models import School


class SchoolProfile(models.Model):
    school = models.OneToOneField(School, on_delete=models.CASCADE, related_name="profile")
    logo = models.ImageField(upload_to="schools/logos/", blank=True, null=True)
    tagline = models.CharField(max_length=255, blank=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    primary_color = models.CharField(max_length=7, default="#1e40af")  # hex
    accent_color = models.CharField(max_length=7, default="#f59e0b")  # hex
    primary_text_color = models.CharField(max_length=7, default="#ffffff")

    class Meta:
        db_table = "school_profiles"

    def __str__(self):
        return f"{self.school.name} — Profile"
