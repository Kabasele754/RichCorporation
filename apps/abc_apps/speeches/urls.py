# =========================
# apps/speeches/urls.py
# =========================
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.abc_apps.speeches.views import SpeechViewSet

router = DefaultRouter()
router.register(r"speeches", SpeechViewSet, basename="speeches")
# router.register(r"actions", SpeechActionsViewSet, basename="speech-actions")

urlpatterns = [path("", include(router.urls))]
