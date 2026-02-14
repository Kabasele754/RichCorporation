from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    TeacherClassGeneralRemarkViewSet,
    TeacherMonthlyObjectiveViewSet,
    TeacherProofScanViewSet,
    TeacherScheduleViewSet,
    TeacherClassViewSet,
    TeacherStudentRemarkViewSet,
    TeacherWeeklyPlanViewSet,
    TeacherQrEnrollmentViewSet,
    TeacherHomeworkViewSet,
    TeacherHomeworkSubmissionViewSet,
)

router = DefaultRouter()
router.register(r"schedule", TeacherScheduleViewSet, basename="teacher-schedule")
router.register(r"classes", TeacherClassViewSet, basename="teacher-classes")
router.register(r"weekly-plans", TeacherWeeklyPlanViewSet, basename="teacher-weekly-plans")
router.register(r"enrollments", TeacherQrEnrollmentViewSet, basename="teacher-enrollments")
router.register(r"homeworks", TeacherHomeworkViewSet, basename="teacher-homeworks")
router.register(r"submissions", TeacherHomeworkSubmissionViewSet, basename="teacher-submissions")
# Remarques et objectifs mensuels
router.register(r"student-remarks", TeacherStudentRemarkViewSet, basename="teacher-student-remarks")
router.register(r"objectives", TeacherMonthlyObjectiveViewSet, basename="teacher-objectives")
router.register(r"class-remarks", TeacherClassGeneralRemarkViewSet, basename="teacher-class-remarks")
router.register(r"proof", TeacherProofScanViewSet, basename="teacher-proof")

urlpatterns = [
    path("", include(router.urls)),
]
