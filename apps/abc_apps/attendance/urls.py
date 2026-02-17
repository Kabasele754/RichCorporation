# apps/attendance/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    StudentAttendanceViewSet,
    TeacherAttendanceConfirmViewSet,
    StudentExamViewSet,
    StudentReenrollmentViewSet,
)

router = DefaultRouter()
router.register(r"student/attendance", StudentAttendanceViewSet, basename="student-attendance")
router.register(r"teacher/attendance", TeacherAttendanceConfirmViewSet, basename="teacher-attendance")
router.register(r"student/exam", StudentExamViewSet, basename="student-exam")
router.register(r"student/reenroll", StudentReenrollmentViewSet, basename="student-reenroll")

urlpatterns = [
    path("", include(router.urls)),
]
