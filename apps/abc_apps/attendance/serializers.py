# =========================
# apps/attendance/serializers.py
# =========================
from rest_framework import serializers
from apps.abc_apps.attendance.models import StudentAttendance, TeacherCheckIn, AttendanceConfirmation

class StudentAttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentAttendance
        fields = "__all__"

class TeacherCheckInSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeacherCheckIn
        fields = "__all__"

class AttendanceConfirmationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceConfirmation
        fields = "__all__"

class StudentScanSerializer(serializers.Serializer):
    qr_payload = serializers.CharField(max_length=255)

class TeacherScanSerializer(serializers.Serializer):
    qr_payload = serializers.CharField(max_length=255)

class ConfirmSerializer(serializers.Serializer):
    session_id = serializers.IntegerField()
    notes = serializers.CharField(required=False, allow_blank=True)
