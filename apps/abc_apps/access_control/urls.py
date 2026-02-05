# =========================================
# apps/abc_apps/access_control/urls.py
# =========================================
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.abc_apps.access_control.views import (
    CredentialViewSet, AccessPointViewSet, AccessRuleViewSet, AccessLogViewSet, AccessScanViewSet
)

router = DefaultRouter()
router.register(r"credentials", CredentialViewSet)
router.register(r"points", AccessPointViewSet)
router.register(r"rules", AccessRuleViewSet)
router.register(r"logs", AccessLogViewSet, basename="access-logs")
router.register(r"", AccessScanViewSet, basename="access-scan")  # provides /scan/

urlpatterns = [path("", include(router.urls))]
