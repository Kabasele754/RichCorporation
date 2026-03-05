from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.abc_apps.attendance.views_admin import AttendanceAdminViewSet
from .views import (
    StudentAttendanceViewSet,
    TeacherAttendanceConfirmViewSet,
    TeacherAttendanceViewSet,
)

router = DefaultRouter()
router.register(r"student/attendance", StudentAttendanceViewSet, basename="student-attendance")
router.register(r"teacher/attendance", TeacherAttendanceViewSet, basename="teacher-attendance")
router.register(r"teacher/attendance-confirm", TeacherAttendanceConfirmViewSet, basename="teacher-attendance-confirm")

# Endpoints pour les QR codes d'examens et de réinscription (v1, sans signature)
router.register(r"student/exam", StudentAttendanceViewSet, basename="student-exam")
router.register(r"student/reenroll", StudentAttendanceViewSet, basename="student-reenroll")

# Endpoints d'administration pour la gestion des tags de salle et des QR codes (Secrétaire ou Admin)
router.register(r"admin/attendance", AttendanceAdminViewSet, basename="attendance-admin")

urlpatterns = [
    path("", include(router.urls)),
]
