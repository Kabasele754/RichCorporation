# apps/attendance/serializers.py
from rest_framework import serializers
from .models import DailyRoomCheckIn, DailyRoomCheckInApproval, StudentExamEntry, ReenrollmentIntent


class DailyRoomCheckInApprovalSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source="teacher.user.get_full_name", read_only=True)
    teacher_code = serializers.CharField(source="teacher.teacher_code", read_only=True, default="")

    class Meta:
        model = DailyRoomCheckInApproval
        fields = ["id", "teacher", "teacher_name", "teacher_code", "approved", "note", "decided_at", "created_at"]


class DailyRoomCheckInSerializer(serializers.ModelSerializer):
    period_key = serializers.CharField(source="period.key", read_only=True)
    room_code = serializers.CharField(source="room.code", read_only=True)
    group_label = serializers.CharField(source="monthly_group.label", read_only=True)

    student_full_name = serializers.CharField(source="student.user.get_full_name", read_only=True)
    student_code = serializers.CharField(source="student.student_code", read_only=True, default="")

    approvals_count = serializers.IntegerField(read_only=True)
    is_fully_confirmed = serializers.BooleanField(read_only=True)
    approvals = DailyRoomCheckInApprovalSerializer(many=True, read_only=True)

    class Meta:
        model = DailyRoomCheckIn
        fields = [
            "id",
            "period", "period_key",
            "date",
            "room", "room_code",
            "monthly_group", "group_label",
            "student", "student_full_name", "student_code",
            "scanned_at", "status", "scanned_by",
            "required_confirmations",
            "approvals_count", "is_fully_confirmed",
            "approvals",
            "created_at",
        ]

class StudentExamEntrySerializer(serializers.ModelSerializer):
    period_key = serializers.CharField(source="period.key", read_only=True)
    group_label = serializers.CharField(source="monthly_group.label", read_only=True)
    room_code = serializers.CharField(source="room.code", read_only=True)

    student_full_name = serializers.CharField(source="student.user.get_full_name", read_only=True)
    student_code = serializers.CharField(source="student.student_code", read_only=True, default="")

    class Meta:
        model = StudentExamEntry
        fields = [
            "id",
            "period", "period_key",
            "date",
            "monthly_group", "group_label",
            "room", "room_code",
            "student", "student_full_name", "student_code",
            "course_id",
            "scanned_at",
            "created_at",
        ]


class ReenrollmentIntentSerializer(serializers.ModelSerializer):
    from_period_key = serializers.CharField(source="from_period.key", read_only=True)
    to_period_key = serializers.CharField(source="to_period.key", read_only=True)
    student_full_name = serializers.CharField(source="student.user.get_full_name", read_only=True)
    student_code = serializers.CharField(source="student.student_code", read_only=True, default="")

    class Meta:
        model = ReenrollmentIntent
        fields = [
            "id",
            "student", "student_full_name", "student_code",
            "from_period", "from_period_key",
            "to_period", "to_period_key",
            "will_return", "reason",
            "status",
            "decided_by", "decided_at",
            "created_at",
        ]
        read_only_fields = ["status", "decided_by", "decided_at", "created_at"]
