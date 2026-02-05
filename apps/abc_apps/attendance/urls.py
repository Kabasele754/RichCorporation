# =========================
# apps/attendance/urls.py
# =========================
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.abc_apps.attendance.views import AttendanceActionsViewSet

router = DefaultRouter()
router.register(r"actions", AttendanceActionsViewSet, basename="attendance-actions")

urlpatterns = [path("", include(router.urls))]
