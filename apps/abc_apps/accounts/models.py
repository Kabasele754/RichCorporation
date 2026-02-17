from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from apps.common.models import TimeStampedModel
from django.utils import timezone


class User(AbstractUser):
    ROLE_CHOICES = [
        ("student", "Student"),
        ("teacher", "Teacher"),
        ("secretary", "Secretary"),
        ("principal", "Principal"),
        ("security", "Security"),
    ]

    email = models.EmailField(unique=True, blank=True, null=True)
    role = models.CharField(max_length=12, choices=ROLE_CHOICES, default="student")

    # ✅ SA-friendly naming + compatible RDC
    # prenom -> first_name (déjà existant)
    # nom    -> last_name  (déjà existant)
    # postnom -> middle_name (ajout)
    middle_name = models.CharField(max_length=80, blank=True, null=True)

    # ✅ Profile photo
    profile_photo = models.ImageField(
        upload_to="profiles/photos/",
        blank=True,
        null=True
    )

    # ✅ Address (South Africa friendly)
    address_line1 = models.CharField(max_length=180, blank=True, null=True)
    address_line2 = models.CharField(max_length=180, blank=True, null=True)
    city = models.CharField(max_length=80, blank=True, null=True)
    province = models.CharField(max_length=80, blank=True, null=True)  # Gauteng, KZN, etc.
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    country = models.CharField(max_length=60, blank=True, null=True, default="South Africa")

    # ✅ Last known GPS location (useful for attendance scan context)
    lat = models.DecimalField(max_digits=20, decimal_places=14, blank=True, null=True)
    lng = models.DecimalField(max_digits=20, decimal_places=14, blank=True, null=True)
    location_updated_at = models.DateTimeField(blank=True, null=True)

    def set_location(self, lat: float, lng: float):
        self.lat = lat
        self.lng = lng
        self.location_updated_at = timezone.now()
        self.save(update_fields=["lat", "lng", "location_updated_at"])

    @property
    def full_name_sa(self):
        # SA style: First + Middle + Last
        parts = [self.first_name, self.middle_name, self.last_name]
        return " ".join([p for p in parts if p])

    @property
    def full_name(self):
        # RDC style: Prenom + Postnom + Nom
        parts = [self.first_name, self.middle_name, self.last_name]
        return " ".join([p for p in parts if p])

    def __str__(self):
        return f"{self.username} ({self.role})"


class StudentProfile(TimeStampedModel):
    STATUS_CHOICES = [("active", "Active"), ("inactive", "Inactive"), ("blocked", "Blocked")]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="student_profile"
    )
    student_code = models.CharField(max_length=50, unique=True)
    current_level = models.CharField(max_length=50)   # e.g. Foundation 3
    group_name = models.CharField(max_length=80)      # e.g. Nelson Mandela
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="active")

    def __str__(self):
        return f"{self.student_code} - {self.user}"


class TeacherProfile(TimeStampedModel):
    SPECIALITY_CHOICES = [("grammar", "Grammar"), ("vocabulary", "Vocabulary"), ("support", "Support")]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="teacher_profile"
    )
    teacher_code = models.CharField(max_length=50, unique=True)
    speciality = models.CharField(max_length=12, choices=SPECIALITY_CHOICES, default="support")

    def __str__(self):
        return f"{self.teacher_code} - {self.user}"


class SecretaryProfile(TimeStampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="secretary_profile"
    )
    secretary_code = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return f"{self.secretary_code} - {self.user}"


class PrincipalProfile(TimeStampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="principal_profile"
    )
    principal_code = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return f"{self.principal_code} - {self.user}"


class SecurityProfile(TimeStampedModel):
    SHIFT_CHOICES = [
        ("morning", "Morning"),
        ("afternoon", "Afternoon"),
        ("night", "Night"),
        ("full_time", "Full Time"), 
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="security_profile"
    )
    security_code = models.CharField(max_length=50, unique=True)
    shift = models.CharField(max_length=12, choices=SHIFT_CHOICES)

    def __str__(self):
        return f"{self.security_code} - {self.user}"


