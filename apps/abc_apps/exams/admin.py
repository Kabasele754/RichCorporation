# =========================
# apps/exams/admin.py
# =========================
from django.contrib import admin
from apps.abc_apps.exams.models import ExamRuleStatus, ExamEntryScan, MonthlyReturnForm

admin.site.register(ExamRuleStatus)
admin.site.register(ExamEntryScan)
admin.site.register(MonthlyReturnForm)
