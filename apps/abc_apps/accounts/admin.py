from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth import get_user_model

from .models import StudentProfile, TeacherProfile, SecretaryProfile, PrincipalProfile, SecurityProfile

User = get_user_model()


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("ABC Role", {"fields": ("role",)}),
    )
    list_display = ("username", "email", "first_name", "last_name", "role", "is_staff", "is_active")
    list_filter = ("role", "is_staff", "is_active")
    search_fields = ("username", "email", "first_name", "last_name")


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ("student_code", "user", "current_level", "group_name", "status", "created_at")
    search_fields = ("student_code", "user__username", "user__email")
    list_filter = ("current_level", "status")


@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = ("teacher_code", "user", "speciality", "created_at")
    search_fields = ("teacher_code", "user__username", "user__email")
    list_filter = ("speciality",)



@admin.register(PrincipalProfile)
class PrincipalProfileAdmin(admin.ModelAdmin):
    list_display = ("principal_code", "user", "created_at")
    search_fields = ("principal_code", "user__username", "user__email")


@admin.register(SecurityProfile)
class SecurityProfileAdmin(admin.ModelAdmin):
    list_display = ("security_code", "user", "shifts_display", "created_at")
    search_fields = ("security_code", "user__username", "user__email")
    # ⚠️ JSONField: list_filter direct parfois ne marche pas bien
    # on enlève list_filter shifts et on filtre via search ou custom filter
    # list_filter = ("shifts",)

    def shifts_display(self, obj):
        # affiche proprement dans l'admin
        if not obj.shifts:
            return "-"
        return ", ".join(obj.shifts)

    shifts_display.short_description = "Shifts"

