# =========================
# apps/accounts/models.py
# =========================
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from apps.common.models import TimeStampedModel

class User(AbstractUser):
    ROLE_CHOICES = [
        ("student", "Student"),
        ("teacher", "Teacher"),
        ("secretary", "Secretary"),
        ("principal", "Principal"),
    ]
    role = models.CharField(max_length=12, choices=ROLE_CHOICES, default="student")

    def __str__(self):
        return f"{self.username} ({self.role})"


class StudentProfile(TimeStampedModel):
    STATUS_CHOICES = [("active", "Active"), ("inactive", "Inactive"), ("blocked", "Blocked")]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="student_profile")
    student_code = models.CharField(max_length=50, unique=True)

    current_level = models.CharField(max_length=50)   # e.g. Foundation 3
    group_name = models.CharField(max_length=80)      # e.g. Nelson Mandela
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="active")

    def __str__(self):
        return f"{self.student_code} - {self.user}"


class TeacherProfile(TimeStampedModel):
    SPECIALITY_CHOICES = [("grammar", "Grammar"), ("vocabulary", "Vocabulary"), ("support", "Support")]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="teacher_profile")
    teacher_code = models.CharField(max_length=50, unique=True)
    speciality = models.CharField(max_length=12, choices=SPECIALITY_CHOICES, default="support")

    def __str__(self):
        return f"{self.teacher_code} - {self.user}"
class SecretaryProfile(TimeStampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="secretary_profile")
    secretary_code = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return f"{self.secretary_code} - {self.user}"

class PrincipalProfile(TimeStampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="principal_profile")
    principal_code = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return f"{self.principal_code} - {self.user}"