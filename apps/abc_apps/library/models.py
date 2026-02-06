# =========================================
# apps/library/models.py
# =========================================
from django.conf import settings
from django.db import models
from django.utils import timezone
from apps.common.models import TimeStampedModel

class Item(TimeStampedModel):
    ITEM_TYPE = [
        ("book", "Book"),
        ("material", "Material"),
    ]
    STATUS = [
        ("available", "Available"),
        ("borrowed", "Borrowed"),
        ("maintenance", "Maintenance"),
        ("lost", "Lost"),
    ]

    code = models.CharField(max_length=50, unique=True)  # QR label e.g. ITEM:ABC-BOOK-001
    item_type = models.CharField(max_length=10, choices=ITEM_TYPE)
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)

    # optional for books (foundation/int...)
    level_hint = models.CharField(max_length=50, blank=True)

    status = models.CharField(max_length=12, choices=STATUS, default="available")

    def __str__(self):
        return f"{self.code} - {self.title}"


class Loan(TimeStampedModel):
    PURPOSE = [
        ("reading", "Reading"),
        ("class_use", "Class use"),
        ("prep", "Lesson preparation"),
        ("other", "Other"),
    ]

    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="loans")
    borrowed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="loans")
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="issued_loans"
    )

    purpose = models.CharField(max_length=20, choices=PURPOSE)
    purpose_detail = models.CharField(max_length=255, blank=True)

    borrowed_at = models.DateTimeField(default=timezone.now)
    due_at = models.DateTimeField(null=True, blank=True)

    returned_at = models.DateTimeField(null=True, blank=True)
    return_checked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="checked_returns"
    )

    # reminder tracking
    last_read_reminder_at = models.DateTimeField(null=True, blank=True)
    last_return_reminder_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["borrowed_at"]),
            models.Index(fields=["due_at", "returned_at"]),
        ]

    @property
    def is_open(self):
        return self.returned_at is None

    def __str__(self):
        return f"Loan({self.item.code}) by {self.borrowed_by_id} open={self.is_open}"
