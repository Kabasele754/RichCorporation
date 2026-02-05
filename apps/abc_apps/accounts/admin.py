# =========================
# apps/accounts/admin.py
# =========================
from django.contrib import admin
from django.contrib.auth import get_user_model
from apps.abc_apps.accounts.models import StudentProfile, TeacherProfile

User = get_user_model()

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "username", "email", "role", "is_active", "is_staff")
    list_filter = ("role", "is_active", "is_staff")
    search_fields = ("username", "email")

@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "student_code", "current_level", "group_name", "status", "user")
    list_filter = ("status", "current_level")
    search_fields = ("student_code", "user__username", "user__email")

@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "teacher_code", "speciality", "user")
    list_filter = ("speciality",)
    search_fields = ("teacher_code", "user__username", "user__email")
