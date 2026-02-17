from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import (
    StudentDashboardViewSet,
    StudentWeeklyPlanViewSet,
    StudentHomeworkViewSet,
    StudentObjectivesViewSet,
    StudentRemarksViewSet,
    StudentProofScansViewSet,
)

router = DefaultRouter()
router.register(r"student/dashboard", StudentDashboardViewSet, basename="student-dashboard")
router.register(r"student/weekly-plans", StudentWeeklyPlanViewSet, basename="student-weekly-plans")
router.register(r"student/homeworks", StudentHomeworkViewSet, basename="student-homeworks")
router.register(r"student/objectives", StudentObjectivesViewSet, basename="student-objectives")
router.register(r"student/remarks", StudentRemarksViewSet, basename="student-remarks")
router.register(r"student/proof-scans", StudentProofScansViewSet, basename="student-proof-scans")

urlpatterns = [path("api/", include(router.urls))]
