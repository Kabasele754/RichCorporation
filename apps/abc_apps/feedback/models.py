# =========================
# apps/feedback/models.py
# =========================
from django.db import models
from apps.common.models import TimeStampedModel, month_validator
from apps.abc_apps.accounts.models import StudentProfile, TeacherProfile

class TeacherRemark(TimeStampedModel):
    CATEGORY_CHOICES = [
        ("discipline", "Discipline"),
        ("performance", "Performance"),
        ("attendance", "Attendance"),
        ("attitude", "Attitude"),
    ]
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="remarks")
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.SET_NULL, null=True, related_name="remarks")
    category = models.CharField(max_length=12, choices=CATEGORY_CHOICES)
    text = models.TextField()

class MonthlyStudentReport(TimeStampedModel):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="monthly_reports")
    month = models.CharField(max_length=7, validators=[month_validator])
    summary = models.TextField()
    created_by = models.ForeignKey(TeacherProfile, on_delete=models.SET_NULL, null=True, related_name="created_reports")
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("student", "month")
