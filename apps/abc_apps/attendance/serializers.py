# =========================
# apps/attendance/serializers.py
# =========================
from rest_framework import serializers
from apps.abc_apps.attendance.models import CourseAttendance, StudentAttendance, TeacherCheckIn, AttendanceConfirmation

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


# new serializers for daily room check-in and course attendance can be added here as needed
class RoomScanSerializer(serializers.Serializer):
    qr_payload = serializers.CharField()

class TeacherConfirmSerializer(serializers.Serializer):
    assignment_id = serializers.IntegerField()
    student_id = serializers.IntegerField()
    date = serializers.DateField(required=False)
    status = serializers.ChoiceField(choices=[c[0] for c in CourseAttendance.STATUS], default="present")
    note = serializers.CharField(required=False, allow_blank=True)

class ReenrollIntentCreateSerializer(serializers.Serializer):
    will_return = serializers.BooleanField()
    reason = serializers.CharField(required=False, allow_blank=True)

class ReenrollDecisionSerializer(serializers.Serializer):
    intent_id = serializers.IntegerField()
    decision = serializers.ChoiceField(choices=["approved", "rejected"])