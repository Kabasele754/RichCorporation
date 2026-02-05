# =========================
# apps/feedback/admin.py
# =========================
from django.contrib import admin
from apps.abc_apps.feedback.models import TeacherRemark, MonthlyStudentReport

admin.site.register(TeacherRemark)
admin.site.register(MonthlyStudentReport)
