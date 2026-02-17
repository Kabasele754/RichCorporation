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

            # ✅ NEW
            "start_time", "end_time",

            "period", "period_key",
            "monthly_group", "monthly_group_label",

            "created_by",
            "created_at",
        ]
        read_only_fields = ["created_by", "created_at"]

    def validate(self, attrs):
        """
        Règles:
        1) period auto depuis start_date si period absent
        2) monthly_group.period doit matcher period
        3) titulaire unique par (period, monthly_group)
        4) conflit horaire: même teacher ne peut pas overlap
        5) doublon exact: même teacher + group + course (dans la même période) interdit
        """
        instance = getattr(self, "instance", None)

        period = attrs.get("period") or (instance.period if instance else None)
        monthly_group = attrs.get("monthly_group") or (instance.monthly_group if instance else None)
        start_date = attrs.get("start_date") or (instance.start_date if instance else None)

        end_date = attrs.get("end_date") if "end_date" in attrs else (instance.end_date if instance else None)

        start_time = attrs.get("start_time") if "start_time" in attrs else (instance.start_time if instance else None)
        end_time = attrs.get("end_time") if "end_time" in attrs else (instance.end_time if instance else None)

        teacher = attrs.get("teacher") or (instance.teacher if instance else None)
        course = attrs.get("course") or (instance.course if instance else None)
        classroom = attrs.get("classroom") or (instance.classroom if instance else None)
        is_titular = attrs.get("is_titular") if "is_titular" in attrs else (instance.is_titular if instance else False)

        # 1) auto period
        if start_date and period is None:
            period = get_or_create_period_from_date(start_date)
            attrs["period"] = period

        # 2) group must have period
        if monthly_group and (period is None):
            raise serializers.ValidationError({"period": "Period is required when monthly_group is provided."})

        if monthly_group and period and monthly_group.period_id != period.id:
            raise serializers.ValidationError({"monthly_group": "monthly_group does not belong to this period."})

        # 3) time coherence
        if (start_time and not end_time) or (end_time and not start_time):
            raise serializers.ValidationError({"start_time": "Provide both start_time and end_time."})
        if start_time and end_time and start_time >= end_time:
            raise serializers.ValidationError({"start_time": "start_time must be < end_time."})

        # Base queryset: same period
        qs = TeacherCourseAssignment.objects.all()
        if period:
            qs = qs.filter(period=period)
        if instance:
            qs = qs.exclude(id=instance.id)

        # 4) titulaire unique (en plus du DB constraint)
        if is_titular and monthly_group and period:
            if qs.filter(monthly_group=monthly_group, is_titular=True).exists():
                raise serializers.ValidationError({
                    "is_titular": "This class already has a titular teacher for this period."
                })

        # 5) doublon exact
        if teacher and course and monthly_group and period:
            if qs.filter(teacher=teacher, course=course, monthly_group=monthly_group).exists():
                raise serializers.ValidationError("This teacher is already assigned to this course in this class for the period.")

        # 6) conflit horaire teacher (overlap)
        # overlap: A.start < B.end AND B.start < A.end
        if teacher and period and start_time and end_time:
            conflict_teacher = qs.filter(
                teacher=teacher,
                start_time__isnull=False,
                end_time__isnull=False,
                start_time__lt=end_time,
                end_time__gt=start_time,
            )
            # Optionnel: aussi vérifier start_date/end_date overlap si tu utilises des plages
            # Ici on suppose assignment mensuel => même period suffit.
            if conflict_teacher.exists():
                raise serializers.ValidationError({
                    "start_time": "Teacher has another assignment that overlaps this time slot."
                })

        # 7) option: conflit salle (room) même créneau
        if classroom and period and start_time and end_time:
            conflict_room = qs.filter(
                classroom=classroom,
                start_time__isnull=False,
                end_time__isnull=False,
                start_time__lt=end_time,
                end_time__gt=start_time,
            )
            if conflict_room.exists():
                raise serializers.ValidationError({
                    "classroom": "This room already has another class at the same time."
                })

        return attrs
    
class MonthlyGoalSerializer(serializers.ModelSerializer):
    class Meta:
        model = MonthlyGoal
        fields = "__all__"
