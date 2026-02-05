# =========================
# apps/exams/models.py
# =========================
from django.db import models
from django.utils import timezone
from apps.common.models import TimeStampedModel, month_validator
from apps.abc_apps.accounts.models import StudentProfile, TeacherProfile
from apps.abc_apps.academics.models import ClassRoom
from apps.abc_apps.sessions_abc.models import ClassSession

class ExamRuleStatus(TimeStampedModel):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="exam_rules")
    classroom = models.ForeignKey(ClassRoom, on_delete=models.CASCADE, related_name="exam_rules")
    books_completed = models.BooleanField(default=False)
    eligible = models.BooleanField(default=False)
    reason_if_not = models.TextField(blank=True)
    updated_by = models.ForeignKey(TeacherProfile, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        unique_together = ("student", "classroom")

class ExamEntryScan(TimeStampedModel):
    session = models.ForeignKey(ClassSession, on_delete=models.CASCADE, related_name="exam_entry_scans")
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="exam_entry_scans")
    scanned_at = models.DateTimeField(default=timezone.now)
    allowed = models.BooleanField(default=False)
    reason = models.TextField(blank=True)

    class Meta:
        unique_together = ("session", "student")

class MonthlyReturnForm(TimeStampedModel):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="return_forms")
    month = models.CharField(max_length=7, validators=[month_validator])
    will_return = models.BooleanField()
    reason_if_no = models.TextField(blank=True)
    submitted_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("student", "month")
