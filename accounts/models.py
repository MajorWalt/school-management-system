from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = UserManager()

    class Meta:
        db_table = "users"

    def __str__(self):
        return f"{self.first_name} {self.last_name} <{self.email}>"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"


class UserRole(models.Model):
    ROLE_CHOICES = [
        ("admin", "Admin"),
        ("teacher", "Teacher"),
        ("student", "Student"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="roles")
    school = models.ForeignKey("core.School", on_delete=models.CASCADE, related_name="user_roles")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "user_roles"
        unique_together = ("user", "school", "role")

    def __str__(self):
        return f"{self.user} — {self.role} @ {self.school}"
