# =========================
# apps/academics/views.py
# =========================
from django.utils import timezone
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError

from apps.common.pagination import StandardPagination
from apps.common.permissions import IsStaffOrPrincipal, IsSecretary

from apps.abc_apps.academics.models import (
    AcademicLevel,
    AcademicPeriod,
    ClassRoom,
    Course,
    MonthlyClassGroup,
    Room,
    StudentMonthlyEnrollment,
    TeacherCourseAssignment,
    MonthlyGoal,
)

from apps.abc_apps.academics.serializers import (
    AcademicLevelSerializer,
    AcademicPeriodSerializer,
    ClassRoomSerializer,
    CourseSerializer,
    MonthlyClassGroupSerializer,
    RoomSerializer,
    StudentMonthlyEnrollmentSerializer,
    TeacherCourseAssignmentSerializer,
    MonthlyGoalSerializer,
)


# ─────────────────────────────────────────────
# AcademicPeriod
# ─────────────────────────────────────────────
class AcademicPeriodViewSet(ModelViewSet):
    queryset = AcademicPeriod.objects.all()  # requis par DRF
    serializer_class = AcademicPeriodSerializer
    permission_classes = [IsAuthenticated, (IsSecretary | IsStaffOrPrincipal)]
    pagination_class = StandardPagination

    def get_queryset(self):
        now = timezone.now()
        return AcademicPeriod.objects.filter(
            year=now.year,
            month=now.month,
        ).order_by("-year", "-month")

    def perform_destroy(self, instance):
        if instance.is_closed:
            raise ValidationError(
                "This academic period is closed and cannot be deleted."
            )
        super().perform_destroy(instance)


# ─────────────────────────────────────────────
# AcademicLevel
# ─────────────────────────────────────────────
class AcademicLevelViewSet(ModelViewSet):
    queryset = AcademicLevel.objects.all().order_by("order", "label")
    serializer_class = AcademicLevelSerializer
    permission_classes = [IsAuthenticated, (IsSecretary | IsStaffOrPrincipal)]


# ─────────────────────────────────────────────
# Room
# ─────────────────────────────────────────────
class RoomViewSet(ModelViewSet):
    queryset = Room.objects.all().order_by("code")
    serializer_class = RoomSerializer
    permission_classes = [IsAuthenticated, (IsSecretary | IsStaffOrPrincipal)]
    pagination_class = StandardPagination


# ─────────────────────────────────────────────
# MonthlyClassGroup
# ─────────────────────────────────────────────
class MonthlyClassGroupViewSet(ModelViewSet):
    queryset = MonthlyClassGroup.objects.select_related(
        "period", "level", "room"
    )
    serializer_class = MonthlyClassGroupSerializer
    permission_classes = [IsAuthenticated, (IsSecretary | IsStaffOrPrincipal)]
    pagination_class = StandardPagination

    def get_queryset(self):
        qs = super().get_queryset()

        # 🔎 Query params
        period = self.request.query_params.get("period")
        level = self.request.query_params.get("level")
        room = self.request.query_params.get("room")

        # ✅ DEFAULT : mois + année courants
        if not period:
            now = timezone.now()
            qs = qs.filter(
                period__year=now.year,
                period__month=now.month,
            )
        else:
            qs = qs.filter(period_id=period)

        if level:
            qs = qs.filter(level_id=level)

        if room:
            qs = qs.filter(room_id=room)

        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save()

    def perform_destroy(self, instance):
        if instance.period and instance.period.is_closed:
            raise ValidationError(
                "Cannot delete a group in a closed period."
            )

        if instance.students.exists():
            raise ValidationError(
                "Cannot delete this group because it has enrolled students."
            )

        super().perform_destroy(instance)

# ─────────────────────────────────────────────
# StudentMonthlyEnrollment
# ─────────────────────────────────────────────
class StudentMonthlyEnrollmentViewSet(ModelViewSet):
    queryset = StudentMonthlyEnrollment.objects.select_related(
        "period",
        "student", "student__user",
        "group", "group__level", "group__room", "group__period",
    ).all().order_by("-created_at")

    serializer_class = StudentMonthlyEnrollmentSerializer
    permission_classes = [IsAuthenticated, (IsSecretary | IsStaffOrPrincipal)]
    pagination_class = StandardPagination

    def get_queryset(self):
        qs = super().get_queryset()
        period = self.request.query_params.get("period")
        student = self.request.query_params.get("student")
        group = self.request.query_params.get("group")
        status = self.request.query_params.get("status")

        if period:
            qs = qs.filter(period_id=period)
        if student:
            qs = qs.filter(student_id=student)
        if group:
            qs = qs.filter(group_id=group)
        if status:
            qs = qs.filter(status=status)

        return qs

    def perform_update(self, serializer):
        # exemple: bloquer modification si période clôturée
        inst = self.get_object()
        if inst.period and inst.period.is_closed:
            raise ValidationError("Cannot update enrollment in a closed period.")
        serializer.save()

    def perform_destroy(self, instance):
        # exemple: bloquer suppression si période clôturée
        if instance.period and instance.period.is_closed:
            raise ValidationError("Cannot delete enrollment in a closed period.")
        super().perform_destroy(instance)


# ─────────────────────────────────────────────
# TeacherCourseAssignment (hybride)
# ─────────────────────────────────────────────
class TeacherCourseAssignmentViewSet(ModelViewSet):
    queryset = TeacherCourseAssignment.objects.select_related(
        "teacher", "teacher__user",
        "classroom",
        "course",
        "period",
        "monthly_group", "monthly_group__level", "monthly_group__room", "monthly_group__period",
    ).all().order_by("-created_at")

    serializer_class = TeacherCourseAssignmentSerializer
    permission_classes = [IsAuthenticated, (IsSecretary | IsStaffOrPrincipal)]
    pagination_class = StandardPagination

    def get_queryset(self):
        qs = super().get_queryset()

        teacher = self.request.query_params.get("teacher")
        classroom = self.request.query_params.get("classroom")
        course = self.request.query_params.get("course")
        period = self.request.query_params.get("period")
        monthly_group = self.request.query_params.get("monthly_group")

        if not period:
            now = timezone.now()
            qs = qs.filter(period__year=now.year, period__month=now.month)
        else:
            qs = qs.filter(period_id=period)

        if teacher:
            qs = qs.filter(teacher_id=teacher)
        if classroom:
            qs = qs.filter(classroom_id=classroom)
        if course:
            qs = qs.filter(course_id=course)
        if monthly_group:
            qs = qs.filter(monthly_group_id=monthly_group)

        return qs

    def perform_create(self, serializer):
        period = serializer.validated_data.get("period")
        if period and period.is_closed:
            raise ValidationError("Cannot create assignment in a closed period.")
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        inst = self.get_object()
        if inst.period and inst.period.is_closed:
            raise ValidationError("Cannot update assignment in a closed period.")
        # aussi si period changé
        period = serializer.validated_data.get("period")
        if period and period.is_closed:
            raise ValidationError("Cannot move assignment to a closed period.")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.period and instance.period.is_closed:
            raise ValidationError("Cannot delete assignment in a closed period.")
        super().perform_destroy(instance)
# ─────────────────────────────────────────────
# ClassRoom
# ─────────────────────────────────────────────
class ClassRoomViewSet(ModelViewSet):
    queryset = ClassRoom.objects.all().order_by("-created_at")
    serializer_class = ClassRoomSerializer
    permission_classes = [IsAuthenticated, (IsSecretary | IsStaffOrPrincipal)]
    pagination_class = StandardPagination


# ─────────────────────────────────────────────
# Course
# ─────────────────────────────────────────────
class CourseViewSet(ModelViewSet):
    queryset = Course.objects.all().order_by("name")
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated, (IsSecretary | IsStaffOrPrincipal)]

    def perform_destroy(self, instance):
        # exemple: empêcher suppression si le cours est utilisé dans des assignments
        if instance.teacher_assignments.exists():  # related_name="teacher_assignments" dans Course
            raise ValidationError("Cannot delete this course because it is assigned to teachers.")
        super().perform_destroy(instance)


# ─────────────────────────────────────────────
# MonthlyGoal
# ─────────────────────────────────────────────
class MonthlyGoalViewSet(ModelViewSet):
    queryset = MonthlyGoal.objects.select_related("classroom").all().order_by("-month", "-created_at")
    serializer_class = MonthlyGoalSerializer
    permission_classes = [IsAuthenticated, IsStaffOrPrincipal]
    pagination_class = StandardPagination
