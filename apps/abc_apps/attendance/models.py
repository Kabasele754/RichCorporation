# apps/attendance/models.py
from __future__ import annotations
from django.conf import settings
from django.db import models
from django.db.models import UniqueConstraint
from django.utils import timezone

from apps.common.models import TimeStampedModel
from apps.abc_apps.accounts.models import StudentProfile, TeacherProfile
from apps.abc_apps.academics.models import AcademicPeriod, Room, MonthlyClassGroup, TeacherCourseAssignment
from apps.abc_apps.academics.models import StudentMonthlyEnrollment  # ton modèle enrollment


class DailyRoomCheckIn(TimeStampedModel):
    """
    ✅ Scan présence sur QR statique d'une ROOM.
    Le group est dérivé de l'enrollment du student (période courante).
    """
    STATUS = [
        ("present", "Present"),
        ("late", "Late"),
        ("absent", "Absent"),
        ("excused", "Excused"),
    ]
    SCANNED_BY = [
        ("self_scan", "Self scan"),
        ("teacher_scan", "Teacher scan"),
    ]

    period = models.ForeignKey(AcademicPeriod, on_delete=models.PROTECT, related_name="daily_checkins")
    date = models.DateField()
    room = models.ForeignKey(Room, on_delete=models.PROTECT, related_name="daily_checkins")
    monthly_group = models.ForeignKey(MonthlyClassGroup, on_delete=models.PROTECT, related_name="daily_checkins")

    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="daily_checkins")
    scanned_at = models.DateTimeField(default=timezone.now)

    status = models.CharField(max_length=12, choices=STATUS, default="present")
    scanned_by = models.CharField(max_length=12, choices=SCANNED_BY, default="self_scan")

    required_confirmations = models.PositiveSmallIntegerField(default=3)

    class Meta:
        constraints = [
            UniqueConstraint(fields=["date", "room", "student"], name="uniq_checkin_date_room_student"),
        ]
        indexes = [
            models.Index(fields=["period", "date", "room"]),
            models.Index(fields=["monthly_group", "date"]),
            models.Index(fields=["student", "date"]),
        ]

    @property
    def approvals_count(self) -> int:
        return self.approvals.filter(approved=True).count()

    @property
    def is_fully_confirmed(self) -> bool:
        return self.approvals_count >= self.required_confirmations


class DailyRoomCheckInApproval(TimeStampedModel):
    checkin = models.ForeignKey(DailyRoomCheckIn, on_delete=models.CASCADE, related_name="approvals")
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, related_name="daily_checkin_approvals")

    approved = models.BooleanField(default=True)
    note = models.CharField(max_length=255, blank=True, default="")
    decided_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            UniqueConstraint(fields=["checkin", "teacher"], name="uniq_checkin_teacher"),
        ]
        indexes = [
            models.Index(fields=["checkin", "approved"]),
            models.Index(fields=["teacher", "decided_at"]),
        ]

class StudentExamEntry(TimeStampedModel):
    """
    ✅ Jour d'exam: student scan -> autorisé si enrollment.exam_unlock=True
    QR statique group + course optionnel (ou salle exam).
    """
    period = models.ForeignKey(AcademicPeriod, on_delete=models.PROTECT, related_name="exam_entries")
    date = models.DateField()
    monthly_group = models.ForeignKey(MonthlyClassGroup, on_delete=models.PROTECT, related_name="exam_entries")
    room = models.ForeignKey(Room, on_delete=models.PROTECT, related_name="exam_entries")

    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="exam_entries")
    scanned_at = models.DateTimeField(default=timezone.now)

    # optionnel: garder une trace du "course" exam (si tu veux)
    course_id = models.IntegerField(null=True, blank=True)

    class Meta:
        constraints = [
            UniqueConstraint(fields=["date", "monthly_group", "student", "course_id"], name="uniq_exam_entry"),
        ]
        indexes = [
            models.Index(fields=["period", "date", "monthly_group"]),
            models.Index(fields=["student", "date"]),
        ]


class ReenrollmentIntent(TimeStampedModel):
    """
    ✅ Après exam: student dit s'il revient.
    Si oui => on crée enrollment du prochain mois avec status=pending (auto).
    """
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
        constraints = [
            UniqueConstraint(fields=["student", "to_period"], name="uniq_reenroll_intent_student_period")
        ]
        indexes = [
            models.Index(fields=["to_period", "status"]),
            models.Index(fields=["student", "to_period"]),
        ]

class TeacherCheckIn(TimeStampedModel):
    session = models.ForeignKey(MonthlyClassGroup, on_delete=models.CASCADE, related_name="teacher_checkins")
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, related_name="checkins")
    scanned_at = models.DateTimeField(default=timezone.now)
    verified = models.BooleanField(default=False)

    class Meta:
        unique_together = ("session", "teacher")

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
