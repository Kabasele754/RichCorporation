# =========================
# apps/exams/urls.py
# =========================
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.abc_apps.exams.views import ExamRuleStatusViewSet, ExamActionsViewSet

router = DefaultRouter()
router.register(r"rules", ExamRuleStatusViewSet)
router.register(r"actions", ExamActionsViewSet, basename="exam-actions")

urlpatterns = [path("", include(router.urls))]
