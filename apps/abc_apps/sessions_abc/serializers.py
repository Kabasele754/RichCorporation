# =========================
# apps/sessions/serializers.py
# =========================
from rest_framework import serializers
from apps.abc_apps.sessions_abc.models import ClassSession, SessionTeacher, AttendanceToken

class ClassSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClassSession
        fields = "__all__"

class SessionTeacherSerializer(serializers.ModelSerializer):
    class Meta:
        model = SessionTeacher
        fields = "__all__"

class AttendanceTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceToken
        fields = ["id", "session", "qr_payload", "expires_at", "created_at"]

class TokenGenerateSerializer(serializers.Serializer):
    session_id = serializers.IntegerField()
    ttl_minutes = serializers.IntegerField(required=False, min_value=5, max_value=24*60)

class TokenValidateSerializer(serializers.Serializer):
    qr_payload = serializers.CharField(max_length=255)
