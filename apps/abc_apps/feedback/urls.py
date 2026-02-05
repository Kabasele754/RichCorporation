# =========================
# apps/feedback/urls.py
# =========================
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.abc_apps.feedback.views import TeacherRemarkViewSet, MonthlyStudentReportViewSet

router = DefaultRouter()
router.register(r"remarks", TeacherRemarkViewSet)
router.register(r"reports", MonthlyStudentReportViewSet)

urlpatterns = [path("", include(router.urls))]
