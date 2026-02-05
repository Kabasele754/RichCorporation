# =========================================
# apps/abc_apps/gate_security/models.py
# =========================================
from django.conf import settings
from django.db import models
from django.utils import timezone
from apps.common.models import TimeStampedModel

class GateEntry(TimeStampedModel):
    """
    Un enregistrement d'entrée/sortie à la barrière.
    - Staff/Teachers/Secretary/Principal peuvent être liés à un user.
    - Visitors peuvent être "name only".
    - Signature stockée en base64 (simple pour Flutter).
    """

    PERSON_TYPE = [
        ("visitor", "Visitor"),
        ("teacher", "Teacher"),
        ("secretary", "Secretary"),
        ("principal", "Principal"),
        ("staff", "Staff"),
    ]

    PURPOSE = [
        ("class", "Class / Teaching"),
        ("meeting", "Meeting"),
        ("administration", "Administration"),
        ("speech_festival", "Speech Festival"),
        ("delivery", "Delivery"),
        ("other", "Other"),
    ]

    # Optionnel: utilisateur connu (teacher/secretary/principal)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="gate_entries",
    )

    # Pour visitors (ou si pas lié à user)
    full_name = models.CharField(max_length=160)
    person_type = models.CharField(max_length=12, choices=PERSON_TYPE)

    # Pourquoi il vient
    purpose = models.CharField(max_length=20, choices=PURPOSE)
    purpose_detail = models.CharField(max_length=255, blank=True)

    # Signature (dessin sur écran) encodée en base64 (ex: data:image/png;base64,...)
    signature_base64 = models.TextField(blank=True)

    check_in_at = models.DateTimeField(default=timezone.now)
    check_out_at = models.DateTimeField(null=True, blank=True)

    # Agent sécurité (ou staff) qui valide l'entrée
    checked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="gate_entries_checked",
    )

    # Gestion "overstay"
    is_overstayed_notified = models.BooleanField(default=False)
    overstayed_notified_at = models.DateTimeField(null=True, blank=True)

    # Optionnel: si tu veux stocker le contenu du QR scanné (staff badge)
    qr_payload = models.CharField(max_length=255, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["check_in_at"]),
            models.Index(fields=["check_out_at"]),
            models.Index(fields=["person_type", "check_in_at"]),
            models.Index(fields=["is_overstayed_notified", "check_out_at"]),
        ]

    @property
    def is_open(self) -> bool:
        return self.check_out_at is None

    def __str__(self):
        return f"{self.full_name} ({self.person_type}) in={self.check_in_at} out={self.check_out_at}"
