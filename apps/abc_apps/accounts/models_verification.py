from django.conf import settings
from django.db import models
from apps.common.models import TimeStampedModel


class VerificationDocument(TimeStampedModel):
    DOC_TYPES = [
        ("passport", "Passport"),
        ("id_card", "National ID Card"),
        ("driver_license", "Driver License"),
        ("residence", "Residence Permit"),
    ]

    STATUS = [
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="verification_documents",
    )

    doc_type = models.CharField(max_length=20, choices=DOC_TYPES)
    document_number = models.CharField(max_length=80)  # ✅ passport number etc
    country_of_issue = models.CharField(max_length=80, blank=True, default="")
    expiry_date = models.DateField(null=True, blank=True)

    # ✅ image scan / photo
    document = models.FileField(upload_to="verification/ids/")

    status = models.CharField(max_length=12, choices=STATUS, default="PENDING")

    # optional admin notes
    admin_note = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} - {self.doc_type} - {self.document_number} ({self.status})"
