# =========================
# apps/academics/serializers.py
# =========================
from rest_framework import serializers
from apps.abc_apps.academics.models import AcademicLevel, AcademicPeriod, ClassRoom, Course, MonthlyClassGroup, Room, StudentMonthlyEnrollment, TeacherCourseAssignment, MonthlyGoal, get_or_create_period_from_date

class AcademicPeriodSerializer(serializers.ModelSerializer):
    month_name = serializers.SerializerMethodField()
    key = serializers.SerializerMethodField()
    code = serializers.SerializerMethodField()

    class Meta:
        model = AcademicPeriod
        fields = ["id", "year", "month", "month_name", "key", "code", "is_closed"]

    def get_month_name(self, obj): return obj.month_name
    def get_key(self, obj): return obj.key
    def get_code(self, obj): return obj.code


class AcademicLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicLevel
        fields = ["id", "code", "label", "order"]


class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ["id", "code", "name", "capacity", "is_active"]


class MonthlyClassGroupSerializer(serializers.ModelSerializer):
    period_key = serializers.CharField(source="period.key", read_only=True)
    level_label = serializers.CharField(source="level.label", read_only=True)
    room_code = serializers.CharField(source="room.code", read_only=True)
    label = serializers.CharField(read_only=True)

    class Meta:
        model = MonthlyClassGroup
        fields = [
            "id",
            "period", "period_key",
            "level", "level_label",
            "group_name",
            "room", "room_code",
            "label",
            "is_active",
            "created_by",
            "created_at",
        ]
        read_only_fields = ["created_by", "created_at"]

class ClassRoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClassRoom
        fields = "__all__"

class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = "__all__"

# class TeacherCourseAssignmentSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = TeacherCourseAssignment
#         fields = "__all__"

# ─────────────────────────────────────────────
# StudentMonthlyEnrollment
# ─────────────────────────────────────────────
class StudentMonthlyEnrollmentSerializer(serializers.ModelSerializer):
    period_key = serializers.CharField(source="period.key", read_only=True)

    student_full_name = serializers.CharField(source="student.user.get_full_name", read_only=True)
    student_code = serializers.CharField(source="student.student_code", read_only=True, default="")

    group_label = serializers.CharField(source="group.label", read_only=True)
    level_label = serializers.CharField(source="group.level.label", read_only=True)
    room_code = serializers.CharField(source="group.room.code", read_only=True)

    class Meta:
        model = StudentMonthlyEnrollment
        fields = [
            "id",
            "period", "period_key",
            "student", "student_full_name", "student_code",
            "group", "group_label", "level_label", "room_code",
            "status",
            "exam_unlock",   # ✅ NEW
            "created_at",
        ]
        read_only_fields = ["created_at"]

    def validate(self, attrs):
        period = attrs.get("period")
        group = attrs.get("group")
        if period and group and group.period_id != period.id:
            raise serializers.ValidationError({"group": "This group does not belong to the selected period."})
        return attrs



# ─────────────────────────────────────────────
# TeacherCourseAssignment (hybride)
# ─────────────────────────────────────────────
class TeacherCourseAssignmentSerializer(serializers.ModelSerializer):
    # Readable extra fields
    teacher_name = serializers.CharField(source="teacher.user.get_full_name", read_only=True)
    teacher_code = serializers.CharField(source="teacher.teacher_code", read_only=True, default="")

    course_name = serializers.CharField(source="course.name", read_only=True)
    classroom_name = serializers.CharField(source="classroom.name", read_only=True)

    period_key = serializers.CharField(source="period.key", read_only=True)
    monthly_group_label = serializers.CharField(source="monthly_group.label", read_only=True)

    class Meta:
        model = TeacherCourseAssignment
        fields = [
            "id",
            "teacher", "teacher_name", "teacher_code",
            "course", "course_name",
            "classroom", "classroom_name",

            "is_titular",
            "start_date", "end_date",

            # nouveau système
            "period", "period_key",
            "monthly_group", "monthly_group_label",

            "created_by",
            "created_at",
        ]
        read_only_fields = ["created_by", "created_at"]

    def validate(self, attrs):
        """
        ✅ règles simples:
        - si monthly_group est donné => period doit exister (ou sera auto depuis start_date)
        - si period est donné + monthly_group donné => monthly_group.period doit matcher
        """
        period = attrs.get("period")
        monthly_group = attrs.get("monthly_group")
        start_date = attrs.get("start_date")

        # Auto period depuis start_date si absent (tu le fais déjà dans save du model,
        # mais ici on garde cohérent côté validation)
        if start_date and period is None:
            period = get_or_create_period_from_date(start_date)
            attrs["period"] = period

        if monthly_group and attrs.get("period") is None:
            raise serializers.ValidationError({"period": "Period is required when monthly_group is provided."})

        if monthly_group and attrs.get("period") and monthly_group.period_id != attrs["period"].id:
            raise serializers.ValidationError({"monthly_group": "monthly_group does not belong to this period."})

        return attrs

class MonthlyGoalSerializer(serializers.ModelSerializer):
    class Meta:
        model = MonthlyGoal
        fields = "__all__"
