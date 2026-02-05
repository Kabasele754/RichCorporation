# =========================
# apps/attendance/models.py
# =========================
from django.db import models
from django.utils import timezone
from apps.common.models import TimeStampedModel
from apps.abc_apps.sessions_abc.models import ClassSession
from apps.abc_apps.accounts.models import StudentProfile, TeacherProfile

class StudentAttendance(TimeStampedModel):
    STATUS_CHOICES = [("present", "Present"), ("late", "Late"), ("absent", "Absent")]
    SCANNED_BY_CHOICES = [("self_scan", "Self scan"), ("teacher_scan", "Teacher scan")]

    session = models.ForeignKey(ClassSession, on_delete=models.CASCADE, related_name="student_attendances")
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="attendances")

    scanned_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="present")
    scanned_by = models.CharField(max_length=12, choices=SCANNED_BY_CHOICES, default="self_scan")

    class Meta:
        unique_together = ("session", "student")
        indexes = [models.Index(fields=["session", "status"]), models.Index(fields=["student", "scanned_at"])]

class TeacherCheckIn(TimeStampedModel):
    session = models.ForeignKey(ClassSession, on_delete=models.CASCADE, related_name="teacher_checkins")
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, related_name="checkins")
    scanned_at = models.DateTimeField(default=timezone.now)
    verified = models.BooleanField(default=False)

    class Meta:
        unique_together = ("session", "teacher")

class AttendanceConfirmation(TimeStampedModel):
    session = models.ForeignKey(ClassSession, on_delete=models.CASCADE, related_name="confirmations")
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, related_name="attendance_confirmations")
    confirmed_at = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ("session", "teacher")
