# =========================
# apps/attendance/admin.py
# =========================
from django.contrib import admin

from apps.abc_apps.attendance.models import DailyRoomCheckIn, DailyRoomCheckInApproval, ReenrollmentIntent, StudentExamEntry

admin.site.register(DailyRoomCheckIn)
admin.site.register(DailyRoomCheckInApproval)
# admin.site.register(StudentExamEntry)
admin.site.register(ReenrollmentIntent)

