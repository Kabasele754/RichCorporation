# =========================
# apps/attendance/models.py
# =========================
from django.conf import settings
from django.db import models
from django.utils import timezone
from apps.abc_apps.academics.models import AcademicPeriod, Room, TeacherCourseAssignment
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

class DailyRoomCheckIn(TimeStampedModel):
    period = models.ForeignKey(AcademicPeriod, on_delete=models.PROTECT, related_name="room_checkins")
    date = models.DateField()
    room = models.ForeignKey(Room, on_delete=models.PROTECT, related_name="checkins")
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="room_checkins")
    scanned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("date", "room", "student")
        indexes = [
            models.Index(fields=["period", "date", "room"]),
            models.Index(fields=["student", "date"]),
        ]


class CourseAttendance(TimeStampedModel):
    STATUS = [
        ("present", "Present"),
        ("late", "Late"),
        ("left_early", "Left early"),
        ("absent", "Absent"),
        ("excused", "Excused"),
    ]

    period = models.ForeignKey(AcademicPeriod, on_delete=models.PROTECT, related_name="course_attendance")
    date = models.DateField()

    # 🔥 On réutilise TeacherCourseAssignment existant
    assignment = models.ForeignKey(
        TeacherCourseAssignment, on_delete=models.PROTECT, related_name="attendance"
    )

    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="course_attendance")
    status = models.CharField(max_length=12, choices=STATUS, default="present")

    confirmed_by = models.ForeignKey(TeacherProfile, on_delete=models.PROTECT, related_name="confirmed_attendance")
    confirmed_at = models.DateTimeField(auto_now_add=True)
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = ("date", "assignment", "student")
        indexes = [
            models.Index(fields=["period", "date"]),
            models.Index(fields=["assignment", "date"]),
            models.Index(fields=["student", "date"]),
        ]


class ReenrollmentIntent(TimeStampedModel):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="reenrollment_intents")
    from_period = models.ForeignKey(AcademicPeriod, on_delete=models.PROTECT, related_name="reenroll_from")
    to_period = models.ForeignKey(AcademicPeriod, on_delete=models.PROTECT, related_name="reenroll_to")

    will_return = models.BooleanField()
    reason = models.TextField(blank=True)

    status = models.CharField(
        max_length=12,
        choices=[("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected")],
        default="pending"
    )

    decided_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("student", "to_period")
        indexes = [
            models.Index(fields=["to_period", "status"]),
            models.Index(fields=["student", "to_period"]),
        ]