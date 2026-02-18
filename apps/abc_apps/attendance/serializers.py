# apps/attendance/serializers.py
from rest_framework import serializers
from .models import DailyRoomCheckIn, DailyRoomCheckInApproval, StudentExamEntry, ReenrollmentIntent
from datetime import datetime
from django.utils import timezone

class DailyRoomCheckInApprovalSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source="teacher.user.get_full_name", read_only=True)
    teacher_code = serializers.CharField(source="teacher.teacher_code", read_only=True, default="")

    class Meta:
        model = DailyRoomCheckInApproval
        fields = ["id", "teacher", "teacher_name", "teacher_code", "approved", "note", "decided_at", "created_at"]


class DailyRoomCheckInSerializer(serializers.ModelSerializer):
    period_key = serializers.CharField(source="period.key", read_only=True)
    group_label = serializers.CharField(source="monthly_group.label", read_only=True)
    room_code = serializers.CharField(source="room.code", read_only=True)

    is_fully_confirmed = serializers.BooleanField(read_only=True)

    # ✅ NEW computed fields
    class_start_time = serializers.SerializerMethodField()
    late_grace_min = serializers.SerializerMethodField()
    diff_minutes = serializers.SerializerMethodField()
    late_by_min = serializers.SerializerMethodField()
    within_grace = serializers.SerializerMethodField()

    class Meta:
        model = DailyRoomCheckIn
        fields = [
            "id",
            "period", "period_key",
            "date",
            "room", "room_code",
            "monthly_group", "group_label",
            "student",
            "status",
            "scanned_by",
            "required_confirmations",
            "scanned_at",
            "is_fully_confirmed",
            "created_at",
            # ✅ extra
            "class_start_time",
            "late_grace_min",
            "diff_minutes",
            "late_by_min",
            "within_grace",
        ]

    def _timing(self, obj):
        g = obj.monthly_group
        start_t = getattr(g, "start_time", None)
        grace = int(getattr(g, "late_grace_min", 45) or 45)

        if not start_t:
            return {"start": None, "grace": grace, "diff": None}

        # scanned_at local
        scanned = timezone.localtime(obj.scanned_at)
        start_dt = datetime.combine(obj.date, start_t)
        start_dt = timezone.make_aware(start_dt, timezone.get_current_timezone())

        diff = int((scanned - start_dt).total_seconds() / 60)
        return {"start": start_t.strftime("%H:%M"), "grace": grace, "diff": diff}

    def get_class_start_time(self, obj):
        return self._timing(obj)["start"]

    def get_late_grace_min(self, obj):
        return self._timing(obj)["grace"]

    def get_diff_minutes(self, obj):
        return self._timing(obj)["diff"]

    def get_late_by_min(self, obj):
        t = self._timing(obj)
        if t["diff"] is None:
            return None
        # late_by = minutes after grace
        return max(0, t["diff"] - t["grace"])

    def get_within_grace(self, obj):
        t = self._timing(obj)
        if t["diff"] is None:
            return None
        return t["diff"] <= t["grace"]
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
