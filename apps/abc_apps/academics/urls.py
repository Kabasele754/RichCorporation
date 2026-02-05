# =========================
# apps/academics/urls.py
# =========================
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.abc_apps.academics.views import ClassRoomViewSet, CourseViewSet, TeacherCourseAssignmentViewSet, MonthlyGoalViewSet

router = DefaultRouter()
router.register(r"classrooms", ClassRoomViewSet)
router.register(r"courses", CourseViewSet)
router.register(r"assignments", TeacherCourseAssignmentViewSet)
router.register(r"goals", MonthlyGoalViewSet)

urlpatterns = [path("", include(router.urls))]
