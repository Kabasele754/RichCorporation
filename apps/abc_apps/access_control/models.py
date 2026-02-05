# =========================================
# apps/abc_apps/access_control/models.py
# =========================================
from django.conf import settings
from django.db import models
from django.utils import timezone
from apps.common.models import TimeStampedModel
from apps.abc_apps.academics.models import ClassRoom

class Credential(TimeStampedModel):
    TYPE_CHOICES = [("qr", "QR"), ("nfc", "NFC")]
    STATUS_CHOICES = [("active", "Active"), ("revoked", "Revoked"), ("lost", "Lost")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="credentials")
    cred_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    uid = models.CharField(max_length=120, unique=True)   # NFC UID or QR UID
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="active")
    issued_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [models.Index(fields=["uid", "status"])]

    def __str__(self):
        return f"{self.user} {self.cred_type}:{self.uid} ({self.status})"


class AccessPoint(TimeStampedModel):
    TYPE_CHOICES = [
        ("gate", "Gate"),
        ("room_door", "Room Door"),
        ("inside_checkin", "Inside Check-in"),
    ]

    name = models.CharField(max_length=120)  # e.g. "Gate Main", "Room 2 Door", "Room 2 Inside"
    point_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    is_active = models.BooleanField(default=True)

    # 🔥 Pour le contrôle par classe : porte associée à une ClassRoom
    classroom = models.ForeignKey(ClassRoom, on_delete=models.SET_NULL, null=True, blank=True, related_name="access_points")

    def __str__(self):
        return f"{self.name} ({self.point_type})"


class AccessRule(TimeStampedModel):
    """
    Règles simples (optionnelles).
    Tu peux commencer SANS AccessRule (juste le match classroom) et activer après.
    """
    ROLE_CHOICES = [
        ("student", "Student"),
        ("teacher", "Teacher"),
        ("secretary", "Secretary"),
        ("principal", "Principal"),
        ("visitor", "Visitor"),
        ("staff", "Staff"),
    ]

    access_point = models.ForeignKey(AccessPoint, on_delete=models.CASCADE, related_name="rules")
    role = models.CharField(max_length=12, choices=ROLE_CHOICES)

    # Optionnel : limiter l'accès par horaire (si null => pas de limite)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)

    allow = models.BooleanField(default=True)

    class Meta:
        unique_together = ("access_point", "role")

    def __str__(self):
        return f"{self.access_point} | {self.role} => {'ALLOW' if self.allow else 'DENY'}"


class AccessLog(TimeStampedModel):
    METHOD_CHOICES = [("qr", "QR"), ("nfc", "NFC"), ("manual", "Manual")]

    access_point = models.ForeignKey(AccessPoint, on_delete=models.SET_NULL, null=True, related_name="logs")

    # Known user (student/teacher/secretary/principal)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="access_logs")

    # Visitor entry (from gate_security)
    visitor_entry = models.ForeignKey(
        "gate_security.GateEntry",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="access_logs",
    )

    method = models.CharField(max_length=10, choices=METHOD_CHOICES)
    uid = models.CharField(max_length=120)

    allowed = models.BooleanField(default=False)
    reason = models.CharField(max_length=255, blank=True)

    scanned_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [
            models.Index(fields=["uid", "scanned_at"]),
            models.Index(fields=["allowed", "scanned_at"]),
            models.Index(fields=["access_point", "scanned_at"]),
        ]

    def __str__(self):
        who = self.user.username if self.user else (self.visitor_entry.full_name if self.visitor_entry else "Unknown")
        return f"{who} @ {self.access_point} allowed={self.allowed}"
