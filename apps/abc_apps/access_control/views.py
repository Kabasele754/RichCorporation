# =========================================
# apps/abc_apps/access_control/views.py
# =========================================
from rest_framework.viewsets import ModelViewSet, ViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework import status

from common.responses import ok, fail
from common.permissions import IsStaffOrPrincipal, IsSecretary
from apps.abc_apps.access_control.models import Credential, AccessPoint, AccessRule, AccessLog
from apps.abc_apps.access_control.serializers import (
    CredentialSerializer, AccessPointSerializer, AccessRuleSerializer, AccessLogSerializer,
    ScanRequestSerializer
)
from apps.abc_apps.access_control.services.access_scan import process_scan

class CredentialViewSet(ModelViewSet):
    queryset = Credential.objects.select_related("user").all().order_by("-issued_at")
    serializer_class = CredentialSerializer
    permission_classes = [IsAuthenticated, (IsSecretary | IsStaffOrPrincipal)]

class AccessPointViewSet(ModelViewSet):
    queryset = AccessPoint.objects.select_related("classroom").all().order_by("name")
    serializer_class = AccessPointSerializer
    permission_classes = [IsAuthenticated, (IsSecretary | IsStaffOrPrincipal)]

class AccessRuleViewSet(ModelViewSet):
    queryset = AccessRule.objects.select_related("access_point").all().order_by("access_point_id", "role")
    serializer_class = AccessRuleSerializer
    permission_classes = [IsAuthenticated, (IsSecretary | IsStaffOrPrincipal)]

class AccessLogViewSet(ModelViewSet):
    queryset = AccessLog.objects.select_related("access_point", "user", "visitor_entry").all().order_by("-scanned_at")
    serializer_class = AccessLogSerializer
    permission_classes = [IsAuthenticated, (IsSecretary | IsStaffOrPrincipal)]
    http_method_names = ["get", "head", "options"]  # read-only

class AccessScanViewSet(ViewSet):
    """
    POST /api/access/scan/
    Body:
      { "uid": "...", "access_point_id": 1, "method": "qr" }

    Response:
      { allowed, reason, access_log_id, person_name, role/person_type }
    """
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["post"], url_path="scan")
    def scan(self, request):
        ser = ScanRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        uid = ser.validated_data["uid"]
        ap_id = ser.validated_data["access_point_id"]
        method = ser.validated_data.get("method", "qr")

        try:
            access_point = AccessPoint.objects.select_related("classroom").get(id=ap_id)
        except AccessPoint.DoesNotExist:
            return fail("Access point not found", status=404)

        try:
            allowed, reason, log = process_scan(uid=uid, access_point=access_point, method=method)

            payload = {
                "allowed": allowed,
                "reason": reason,
                "access_log_id": log.id,
            }

            if log.user:
                payload["person_name"] = (f"{log.user.first_name} {log.user.last_name}").strip() or log.user.username
                payload["role"] = getattr(log.user, "role", "")
            elif log.visitor_entry:
                payload["person_name"] = log.visitor_entry.full_name
                payload["person_type"] = log.visitor_entry.person_type

            return ok(payload, message="Scan processed", status=status.HTTP_200_OK)
        except Exception as e:
            return fail(str(e), status=400)
