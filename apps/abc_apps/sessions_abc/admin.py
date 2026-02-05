# =========================
# apps/sessions/admin.py
# =========================
from django.contrib import admin
from apps.abc_apps.sessions_abc.models import ClassSession, SessionTeacher, AttendanceToken

admin.site.register(ClassSession)
admin.site.register(SessionTeacher)
admin.site.register(AttendanceToken)
