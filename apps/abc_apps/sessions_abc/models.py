# =========================
# apps/sessions/models.py
# =========================
from django.conf import settings
from django.db import models
from django.utils import timezone
from apps.abc_apps.academics.models import ClassRoom
from apps.common.models import TimeStampedModel
from apps.abc_apps.academics.models import ClassRoom
from apps.abc_apps.accounts.models import TeacherProfile

class ClassSession(TimeStampedModel):
    SESSION_TYPE_CHOICES = [("class", "Class"), ("exam", "Exam"), ("festival", "Festival")]

    classroom = models.ForeignKey(ClassRoom, on_delete=models.CASCADE, related_name="sessions")
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    session_type = models.CharField(max_length=10, choices=SESSION_TYPE_CHOICES, default="class")

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["classroom", "date"]),
            models.Index(fields=["date", "session_type"]),
        ]

class SessionTeacher(TimeStampedModel):
    ROLE_IN_SESSION_CHOICES = [("lead", "Lead"), ("assistant", "Assistant"), ("adjudicator", "Adjudicator")]

    session = models.ForeignKey(ClassSession, on_delete=models.CASCADE, related_name="teachers")
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, related_name="sessions")
    role_in_session = models.CharField(max_length=12, choices=ROLE_IN_SESSION_CHOICES, default="assistant")

    class Meta:
        unique_together = ("session", "teacher")

class AttendanceToken(TimeStampedModel):
    session = models.OneToOneField(ClassSession, on_delete=models.CASCADE, related_name="token")
    qr_payload = models.CharField(max_length=255, unique=True)
    expires_at = models.DateTimeField()

    def is_valid(self):
        return timezone.now() <= self.expires_at
