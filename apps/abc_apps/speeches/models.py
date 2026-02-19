# apps/speeches/models.py
from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator

from apps.abc_apps.commons.models import TimeStampedModel, month_validator
from apps.abc_apps.accounts.models import StudentProfile, TeacherProfile
from apps.abc_apps.academics.models import AcademicPeriod, MonthlyClassGroup, Room


def speech_cover_upload_path(instance, filename: str) -> str:
    return f"speeches/covers/{instance.period_id}/{instance.group_id}/{instance.id}/{filename}"


def speech_audio_upload_path(instance, filename: str) -> str:
    return f"speeches/audio/{instance.speech_id}/{instance.kind}/{filename}"


class Speech(TimeStampedModel):
    AUTHOR_TYPE = [("student", "Student"), ("teacher", "Teacher")]

    STATUS = [
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("needs_revision", "Needs revision"),
        ("corrected", "Corrected"),
        ("coached", "Coached"),
        ("pending_approval", "Pending approval"),
        ("published", "Published"),
        ("rejected", "Rejected"),
    ]

    VISIBILITY = [
        ("private", "Private"),
        ("class", "Class"),
        ("school", "School"),
        ("public", "Public"),
    ]

    # ✅ Context académique
    period = models.ForeignKey(AcademicPeriod, on_delete=models.PROTECT, related_name="speeches", null=True, blank=True,)
    group = models.ForeignKey(MonthlyClassGroup, on_delete=models.PROTECT, related_name="speeches", null=True, blank=True,)
    room = models.ForeignKey(Room, on_delete=models.PROTECT, related_name="speeches", null=True, blank=True,)

    # Auteur
    author_type = models.CharField(max_length=10, choices=AUTHOR_TYPE, default="student")
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, null=True, blank=True, related_name="speeches")
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, null=True, blank=True, related_name="speeches")

    # option: speech mensuel
    month = models.CharField(max_length=7, validators=[month_validator], null=True, blank=True)

    title = models.CharField(max_length=160)
    raw_content = models.TextField()

    # ✅ image (optionnelle) — MAIS obligatoire au publish
    cover_image = models.ImageField(upload_to=speech_cover_upload_path, null=True, blank=True)

    submitted_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default="draft")
    visibility = models.CharField(max_length=10, choices=VISIBILITY, default="private")

    # publish metadata
    published_at = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=["period", "group", "status"]),
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.status})"


class SpeechRevision(TimeStampedModel):
    """
    Correction texte (v1, v2...). Teacher ou staff.
    """
    speech = models.ForeignKey(Speech, on_delete=models.CASCADE, related_name="revisions")
    version = models.PositiveSmallIntegerField(default=1)

    revised_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    revised_content = models.TextField()
    notes = models.TextField(blank=True)
    is_final = models.BooleanField(default=False)

    class Meta:
        unique_together = ("speech", "version")
        ordering = ["version"]


class SpeechCoaching(TimeStampedModel):
    """
    Notes prononciation (peut aussi être “final”).
    """
    speech = models.ForeignKey(Speech, on_delete=models.CASCADE, related_name="coachings")
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.SET_NULL, null=True, related_name="speech_coachings")

    pronunciation_notes = models.TextField(blank=True)
    word_tips = models.JSONField(default=list, blank=True)  # ex: [{"word":"through","tip":"..."}, ...]
    is_final = models.BooleanField(default=False)


class SpeechAudio(TimeStampedModel):
    KIND = [
        ("student_recording", "Student recording"),
        ("teacher_coaching", "Teacher coaching audio"),
        ("tts", "Text to speech"),
    ]
    speech = models.ForeignKey(Speech, on_delete=models.CASCADE, related_name="audios")
    kind = models.CharField(max_length=20, choices=KIND)

    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    audio_file = models.FileField(upload_to=speech_audio_upload_path)

    duration_sec = models.PositiveIntegerField(null=True, blank=True)
    transcript_text = models.TextField(blank=True)
    engine = models.CharField(max_length=40, blank=True)
    voice_name = models.CharField(max_length=60, blank=True)

    is_primary = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=["speech", "kind", "created_at"]),
        ]


class SpeechApproval(TimeStampedModel):
    DECISION = [("approve", "Approve"), ("reject", "Reject")]

    speech = models.OneToOneField(Speech, on_delete=models.CASCADE, related_name="approval")
    decided_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    decision = models.CharField(max_length=10, choices=DECISION)
    reason = models.TextField(blank=True)
    decided_at = models.DateTimeField(default=timezone.now)


class SpeechLike(TimeStampedModel):
    speech = models.ForeignKey(Speech, on_delete=models.CASCADE, related_name="likes")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="speech_likes")

    class Meta:
        unique_together = ("speech", "user")


class SpeechComment(TimeStampedModel):
    speech = models.ForeignKey(Speech, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="speech_comments")
    content = models.TextField()
    is_hidden = models.BooleanField(default=False)


class SpeechShare(TimeStampedModel):
    speech = models.ForeignKey(Speech, on_delete=models.CASCADE, related_name="shares")
    shared_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="speech_shares")
    channel = models.CharField(max_length=30, default="in_app")
    to_user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="speech_shared_to_me")


class SpeechVisibilityGrant(TimeStampedModel):
    speech = models.ForeignKey(Speech, on_delete=models.CASCADE, related_name="visibility_grants")
    granted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="speech_visibility_given")
    to_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="speech_visibility_received")

    class Meta:
        unique_together = ("speech", "to_user")
