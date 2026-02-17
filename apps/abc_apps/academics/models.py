# =========================
# apps/academics/models.py
# =========================
from django.conf import settings
from datetime import date
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db import models
from django.db.models import Q
from django.core.exceptions import ValidationError
from apps.abc_apps.commons.models import TimeStampedModel, month_validator

from apps.abc_apps.accounts.models import StudentProfile, TeacherProfile

# ─────────────────────────────────────────────
# 1) Period (mensuel) - déjà validé
# ─────────────────────────────────────────────
class AcademicPeriod(TimeStampedModel):
    class Month(models.IntegerChoices):
        JAN = 1, _("January")
        FEB = 2, _("February")
        MAR = 3, _("March")
        APR = 4, _("April")
        MAY = 5, _("May")
        JUN = 6, _("June")
        JUL = 7, _("July")
        AUG = 8, _("August")
        SEP = 9, _("September")
        OCT = 10, _("October")
        NOV = 11, _("November")
        DEC = 12, _("December")

    year = models.PositiveIntegerField()
    month = models.PositiveSmallIntegerField(choices=Month.choices)  # 1..12
    is_closed = models.BooleanField(default=False)

    class Meta:
        unique_together = ("year", "month")
        indexes = [models.Index(fields=["year", "month"])]

    @property
    def month_name(self) -> str:
        return self.get_month_display()

    @property
    def key(self) -> str:
        # ex: "February 2026"
        return f"{self.month_name} {self.year}"

    @property
    def code(self) -> str:
        # ex: "2026-02"
        return f"{self.year:04d}-{self.month:02d}"

    def __str__(self) -> str:
        return self.key


def get_or_create_period_from_date(dt: date) -> "AcademicPeriod":
    p, _ = AcademicPeriod.objects.get_or_create(year=dt.year, month=dt.month)
    return p


def get_current_period() -> "AcademicPeriod":
    today = timezone.localdate()
    return get_or_create_period_from_date(today)


# ─────────────────────────────────────────────
# 2) Level (académique)
# ─────────────────────────────────────────────
class AcademicLevel(TimeStampedModel):
    # ex: FOUNDATION_1, BASIC_2, INTERMEDIATE_1, ADVANCED_2
    code = models.CharField(max_length=50, unique=True)
    # ex: "Foundation 1"
    label = models.CharField(max_length=80)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "label"]

    def __str__(self) -> str:
        return self.label


# ─────────────────────────────────────────────
# 3) Room (salle physique)
# ─────────────────────────────────────────────
class Room(TimeStampedModel):
    # ex: "R1", "R2", "LAB-A"
    code = models.CharField(max_length=20, unique=True)
    # ex: "Room 2 - Main Building"
    name = models.CharField(max_length=120)
    capacity = models.PositiveIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} • {self.name}"


class ClassRoom(TimeStampedModel):
    name = models.CharField(max_length=120)
    level = models.CharField(max_length=50)
    group_name = models.CharField(max_length=80)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("level", "group_name")

    def __str__(self):
        return self.name

class Course(TimeStampedModel):
    name = models.CharField(max_length=60, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

# ─────────────────────────────────────────────
# 4) ✅ MonthlyClassGroup (modèle clé)
# ─────────────────────────────────────────────
class MonthlyClassGroup(TimeStampedModel):
    period = models.ForeignKey(
        AcademicPeriod,
        on_delete=models.CASCADE,
        
        related_name="class_groups",
    )

    level = models.ForeignKey(
        AcademicLevel,
        on_delete=models.PROTECT,
        
        related_name="monthly_groups",
    )

    # ex: "A", "B", "C"  (ou "Morning", "Evening" si besoin)
    group_name = models.CharField(max_length=80)

    room = models.ForeignKey(
        Room,
        on_delete=models.PROTECT,
        related_name="monthly_groups",
    )

    is_active = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_monthly_groups",
    )

    class Meta:
        # ✅ autorise 2 rooms pour le même level+group MAIS pas la même room 2 fois
        unique_together = ("period", "level", "group_name", "room")
        indexes = [
            models.Index(fields=["period", "level"]),
            models.Index(fields=["period", "room"]),
            models.Index(fields=["level", "group_name"]),
        ]
        ordering = ["-period__year", "-period__month", "level__order", "group_name", "room__code"]

    @property
    def label(self) -> str:
        # ex: "Foundation 1 A • R2"
        return f"{self.level.label} {self.group_name} • {self.room.code}"

    def __str__(self) -> str:
        # ex: "February 2026 • Foundation 1 A • R2"
        return f"{self.period.key} • {self.level.label} {self.group_name} • {self.room.code}"


# ✅ NOUVEAU : inscription mensuelle de l’étudiant
class StudentMonthlyEnrollment(TimeStampedModel):
    period = models.ForeignKey(AcademicPeriod, on_delete=models.CASCADE, related_name="student_enrollments")
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="monthly_enrollments")
    group = models.ForeignKey(MonthlyClassGroup, on_delete=models.PROTECT, related_name="students")
    status = models.CharField(
        max_length=12,
        choices=[("pending", "Pending"), ("active", "Active"), ("inactive", "Inactive")],
        default="pending",
    )
    # ✅ NEW: autorisation examen
    exam_unlock = models.BooleanField(default=False)

    class Meta:
        unique_together = ("period", "student", "group")
        indexes = [
            models.Index(fields=["period", "group"]),
            models.Index(fields=["student", "period"]),
        ]


# ✅ EXISTANT (modifié) : assignment teacher↔course
class TeacherCourseAssignment(TimeStampedModel):
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, related_name="course_assignments")
    classroom = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="teacher_assignments")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="teacher_assignments")

    is_titular = models.BooleanField(default=False)

    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)

    # ✅ NEW
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="created_course_assignments"
    )

    period = models.ForeignKey(
        AcademicPeriod, on_delete=models.PROTECT,
        null=True, blank=True, related_name="teacher_assignments"
    )
    monthly_group = models.ForeignKey(
        MonthlyClassGroup, on_delete=models.PROTECT,
        null=True, blank=True, related_name="teacher_assignments"
    )

    class Meta:
        indexes = [
            models.Index(fields=["period", "monthly_group"]),
            models.Index(fields=["period", "teacher"]),
            models.Index(fields=["teacher", "start_date"]),
            models.Index(fields=["classroom", "start_date"]),
        ]
        # ⚠️ DB-level constraints for titular uniqueness (safe + strong)
        constraints = [
            # ✅ 1 titulaire max par (period, monthly_group)
            models.UniqueConstraint(
                fields=["period", "monthly_group"],
                condition=Q(is_titular=True),
                name="uniq_titular_per_group_per_period",
            ),
        ]

    def clean(self):
        # ✅ time coherence
        if (self.start_time and not self.end_time) or (self.end_time and not self.start_time):
            raise ValidationError("start_time and end_time must be provided together.")
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError("start_time must be < end_time.")

class MonthlyGoal(TimeStampedModel):
    month = models.CharField(max_length=7, validators=[month_validator])
    goal_text = models.TextField()

    level = models.CharField(max_length=50, blank=True)
    classroom = models.ForeignKey(Room, on_delete=models.CASCADE, null=True, blank=True, related_name="goals")

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="created_goals"
    )
    
    
    
    