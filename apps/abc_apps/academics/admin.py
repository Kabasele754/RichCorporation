# =========================
# apps/academics/admin.py
# =========================
from django.contrib import admin
from apps.abc_apps.academics.models import ClassRoom, Course, TeacherCourseAssignment, MonthlyGoal

admin.site.register(ClassRoom)
admin.site.register(Course)
admin.site.register(TeacherCourseAssignment)
admin.site.register(MonthlyGoal)
