# =========================
# apps/attendance/admin.py
# =========================
from django.contrib import admin
from apps.abc_apps.attendance.models import StudentAttendance, TeacherCheckIn, AttendanceConfirmation

admin.site.register(StudentAttendance)
admin.site.register(TeacherCheckIn)
admin.site.register(AttendanceConfirmation)
