# =========================
# apps/speeches/models.py
# =========================
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.common.models import TimeStampedModel, month_validator
from apps.abc_apps.accounts.models import StudentProfile, TeacherProfile

class Speech(TimeStampedModel):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("corrected", "Corrected"),
        ("coached", "Coached"),
        ("shortlisted", "Shortlisted"),
        ("published", "Published"),
        ("rejected", "Rejected"),
    ]

    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="speeches")
    month = models.CharField(max_length=7, validators=[month_validator])
    title = models.CharField(max_length=160)
    raw_content = models.TextField()
    submitted_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="draft")

    class Meta:
        unique_together = ("student", "month")

class SpeechCorrection(TimeStampedModel):
    speech = models.OneToOneField(Speech, on_delete=models.CASCADE, related_name="correction")
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.SET_NULL, null=True, related_name="speech_corrections")
    corrected_content = models.TextField()
    correction_notes = models.TextField(blank=True)
    corrected_at = models.DateTimeField(default=timezone.now)

class SpeechCoaching(TimeStampedModel):
    speech = models.OneToOneField(Speech, on_delete=models.CASCADE, related_name="coaching")
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.SET_NULL, null=True, related_name="speech_coachings")
    pronunciation_notes = models.TextField(blank=True)
    coached_at = models.DateTimeField(default=timezone.now)

class SpeechScore(TimeStampedModel):
    speech = models.ForeignKey(Speech, on_delete=models.CASCADE, related_name="scores")
    adjudicator = models.ForeignKey(TeacherProfile, on_delete=models.SET_NULL, null=True, related_name="speech_scores")
    score = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    comments = models.TextField(blank=True)
    scored_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("speech", "adjudicator")

class SpeechPublicationDecision(TimeStampedModel):
    DECISION_CHOICES = [("publish", "Publish"), ("reject", "Reject")]

    speech = models.OneToOneField(Speech, on_delete=models.CASCADE, related_name="publication_decision")
    decided_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    decision = models.CharField(max_length=10, choices=DECISION_CHOICES)
    reason = models.TextField(blank=True)
    decided_at = models.DateTimeField(default=timezone.now)
