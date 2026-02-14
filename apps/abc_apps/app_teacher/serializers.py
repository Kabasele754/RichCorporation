from rest_framework import serializers

# ✅ Import tes models existants (adapte)
from apps.abc_apps.academics.models import (
    StudentProfile,
   
)

from .models import ClassGeneralRemark, StudentMonthlyObjective, ClassGeneralRemark, StudentProofScan, StudentRemark, WeeklyTeachingPlan, Homework, HomeworkSubmission


class StudentMiniSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="user.get_full_name", read_only=True)
    email = serializers.CharField(source="user.email", read_only=True)

    class Meta:
        model = StudentProfile
        fields = ["id", "student_code", "full_name", "email", "current_level", "group_name", "status"]

# ─────────────────────────────────────────────
# WeeklyTeachingPlan & Homework
# ─────────────────────────────────────────────

class WeeklyTeachingPlanSerializer(serializers.ModelSerializer):
    course_name = serializers.CharField(source="course.name", read_only=True)
    group_label = serializers.CharField(source="monthly_group.label", read_only=True)
    period_key = serializers.CharField(source="period.key", read_only=True)

    class Meta:
        model = WeeklyTeachingPlan
        fields = "__all__"
        read_only_fields = ["teacher", "period", "created_at", "updated_at"]

# ✅ BONUS : serializer pour les devoirs (si tu veux faire la partie devoirs)

class HomeworkSerializer(serializers.ModelSerializer):
    group_label = serializers.CharField(source="group.label", read_only=True)
    course_name = serializers.CharField(source="course.name", read_only=True)
    period_key = serializers.CharField(source="period.key", read_only=True)
    teacher_name = serializers.CharField(source="teacher.user.get_full_name", read_only=True)

    class Meta:
        model = Homework
        fields = "__all__"
        read_only_fields = ["teacher", "period", "created_at", "updated_at"]

# ✅ BONUS : serializer pour les submissions de devoirs (si tu veux faire la partie devoirs)

class HomeworkSubmissionSerializer(serializers.ModelSerializer):
    student_full_name = serializers.CharField(source="student.user.get_full_name", read_only=True)
    student_code = serializers.CharField(source="student.student_code", read_only=True, default="")

    class Meta:
        model = HomeworkSubmission
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at"]


# ✅ QR enroll payload
class EnrollByQrPayloadSerializer(serializers.Serializer):
    group_id = serializers.IntegerField()
    qr_data = serializers.CharField()

    status = serializers.ChoiceField(
        choices=[("pending", "Pending"), ("active", "Active"), ("inactive", "Inactive")],
        default="active",
        required=False
    )
    

# ─────────────────────────────────────────────
# Remarques et objectifs mensuels
# ─────────────────────────────────────────────
    
class StudentProofScanSerializer(serializers.ModelSerializer):
    student_full_name = serializers.CharField(source="student.user.get_full_name", read_only=True)
    student_code = serializers.CharField(source="student.student_code", read_only=True)
    period_key = serializers.CharField(source="period.key", read_only=True)
    group_label = serializers.CharField(source="group.label", read_only=True)
    course_name = serializers.CharField(source="course.name", read_only=True)

    class Meta:
        model = StudentProofScan
        fields = "__all__"
        read_only_fields = ["teacher", "period", "scanned_at"]


class StudentRemarkSerializer(serializers.ModelSerializer):
    student_full_name = serializers.CharField(source="student.user.get_full_name", read_only=True)
    student_code = serializers.CharField(source="student.student_code", read_only=True)
    period_key = serializers.CharField(source="period.key", read_only=True)
    group_label = serializers.CharField(source="group.label", read_only=True)
    course_name = serializers.CharField(source="course.name", read_only=True)

    class Meta:
        model = StudentRemark
        fields = "__all__"
        read_only_fields = ["teacher", "period", "created_at"]


class StudentMonthlyObjectiveSerializer(serializers.ModelSerializer):
    student_full_name = serializers.CharField(source="student.user.get_full_name", read_only=True)
    student_code = serializers.CharField(source="student.student_code", read_only=True)
    period_key = serializers.CharField(source="period.key", read_only=True)
    group_label = serializers.CharField(source="group.label", read_only=True)

    class Meta:
        model = StudentMonthlyObjective
        fields = "__all__"
        read_only_fields = ["teacher", "period", "created_at"]


class ClassGeneralRemarkSerializer(serializers.ModelSerializer):
    period_key = serializers.CharField(source="period.key", read_only=True)
    group_label = serializers.CharField(source="group.label", read_only=True)
    teacher_name = serializers.CharField(source="teacher.user.get_full_name", read_only=True)

    class Meta:
        model = ClassGeneralRemark
        fields = "__all__"
        read_only_fields = ["teacher", "period", "created_at"]
