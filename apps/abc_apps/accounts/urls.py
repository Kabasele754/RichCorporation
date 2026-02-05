# =========================
# apps/accounts/urls.py
# =========================
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.abc_apps.accounts.views import MeViewSet, SecretaryStudentAdminViewSet

router = DefaultRouter()
router.register(r"me", MeViewSet, basename="me")
router.register(r"secretary/students", SecretaryStudentAdminViewSet, basename="secretary-students")

urlpatterns = [
    path("", include(router.urls)),
]
