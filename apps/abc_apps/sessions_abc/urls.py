# =========================
# apps/sessions/urls.py
# =========================
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.abc_apps.sessions_abc.views import ClassSessionViewSet, SessionTeacherViewSet, QRViewSet

router = DefaultRouter()
router.register(r"sessions", ClassSessionViewSet)
router.register(r"session-teachers", SessionTeacherViewSet)
router.register(r"qr", QRViewSet, basename="qr")

urlpatterns = [path("", include(router.urls))]
