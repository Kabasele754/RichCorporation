# =========================
# apps/academics/urls.py
# =========================
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.abc_apps.academics.views import AcademicLevelViewSet, AcademicPeriodViewSet, ClassRoomViewSet, CourseViewSet, MonthlyClassGroupViewSet, RoomViewSet, StudentMonthlyEnrollmentViewSet, StudentMonthlyEnrollmentViewSet, TeacherCourseAssignmentViewSet, MonthlyGoalViewSet

router = DefaultRouter()
router.register(r"classrooms", ClassRoomViewSet)
router.register(r"courses", CourseViewSet)
router.register(r"student", StudentMonthlyEnrollmentViewSet, basename="student-enrollments")
router.register(r"teacher-assignments", TeacherCourseAssignmentViewSet, basename="teacher-assignments")
router.register(r"assignments", TeacherCourseAssignmentViewSet)
router.register(r"goals", MonthlyGoalViewSet)
router.register(r"periods", AcademicPeriodViewSet)
router.register(r"levels", AcademicLevelViewSet)
router.register(r"rooms", RoomViewSet)
router.register(r"monthly-groups", MonthlyClassGroupViewSet)

urlpatterns = [path("", include(router.urls))]
