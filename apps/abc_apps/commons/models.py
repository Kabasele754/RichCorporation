# =========================
# common/models.py
# =========================
from django.core.validators import RegexValidator
from django.db import models

month_validator = RegexValidator(
    regex=r"^\d{4}-(0[1-9]|1[0-2])$",
    message="Month must be in format YYYY-MM (e.g. 2026-02).",
)

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        abstract = True
