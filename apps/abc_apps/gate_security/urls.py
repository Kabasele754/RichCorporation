# =========================================
# apps/abc_apps/gate_security/urls.py
# =========================================
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.abc_apps.gate_security.views import GateSecurityViewSet

router = DefaultRouter()
router.register(r"entries", GateSecurityViewSet, basename="gate-entries")

urlpatterns = [
    path("", include(router.urls)),
]
