# =========================
# apps/sessions/views.py
# =========================
from rest_framework.viewsets import ModelViewSet, ViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework import status

from apps.common.responses import ok, fail
from apps.common.permissions import IsSecretary, IsStaffOrPrincipal
from apps.abc_apps.sessions_abc.models import ClassSession, SessionTeacher
from apps.abc_apps.sessions_abc.serializers import (
    ClassSessionSerializer, SessionTeacherSerializer,
    AttendanceTokenSerializer, TokenGenerateSerializer, TokenValidateSerializer
)
from apps.abc_apps.sessions_abc.services.qr import generate_or_refresh_token, validate_payload

class ClassSessionViewSet(ModelViewSet):
    queryset = ClassSession.objects.select_related("classroom").all().order_by("-date", "-start_time")
    serializer_class = ClassSessionSerializer
    permission_classes = [IsAuthenticated, (IsSecretary | IsStaffOrPrincipal)]

class SessionTeacherViewSet(ModelViewSet):
    queryset = SessionTeacher.objects.select_related("session", "teacher").all().order_by("-created_at")
    serializer_class = SessionTeacherSerializer
    permission_classes = [IsAuthenticated, (IsSecretary | IsStaffOrPrincipal)]

class QRViewSet(ViewSet):
    permission_classes = [IsAuthenticated, (IsSecretary | IsStaffOrPrincipal)]

    @action(detail=False, methods=["post"])
    def generate(self, request):
        ser = TokenGenerateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        session = ClassSession.objects.get(id=ser.validated_data["session_id"])
        ttl = ser.validated_data.get("ttl_minutes")
        token = generate_or_refresh_token(session, ttl_minutes=ttl or 180)
        return ok(AttendanceTokenSerializer(token).data, message="Token generated", status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"])
    def validate(self, request):
        ser = TokenValidateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            token = validate_payload(ser.validated_data["qr_payload"])
            return ok({"session_id": token.session_id, "expires_at": token.expires_at}, message="Token valid")
        except Exception as e:
            return fail(str(e), status=status.HTTP_400_BAD_REQUEST)
