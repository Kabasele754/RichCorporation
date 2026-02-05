# =========================
# apps/academics/models.py
# =========================
from django.conf import settings
from django.db import models
from apps.common.models import TimeStampedModel, month_validator

from apps.abc_apps.accounts.models import TeacherProfile

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

class TeacherCourseAssignment(TimeStampedModel):
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, related_name="course_assignments")
    classroom = models.ForeignKey(ClassRoom, on_delete=models.CASCADE, related_name="teacher_assignments")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="teacher_assignments")

    is_titular = models.BooleanField(default=False)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="created_course_assignments"
    )

    class Meta:
        indexes = [
            models.Index(fields=["teacher", "classroom"]),
            models.Index(fields=["classroom", "course"]),
        ]

class MonthlyGoal(TimeStampedModel):
    month = models.CharField(max_length=7, validators=[month_validator])
    goal_text = models.TextField()

    level = models.CharField(max_length=50, blank=True)
    classroom = models.ForeignKey(ClassRoom, on_delete=models.CASCADE, null=True, blank=True, related_name="goals")

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="created_goals"
    )
