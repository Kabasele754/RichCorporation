# =========================
# apps/academics/views.py
# =========================
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from commons.pagination import StandardPagination
from apps.abc_apps.academics.models import ClassRoom, Course, TeacherCourseAssignment, MonthlyGoal
from apps.abc_apps.academics.serializers import (
    ClassRoomSerializer, CourseSerializer, TeacherCourseAssignmentSerializer, MonthlyGoalSerializer
)
from commons.permissions import IsStaffOrPrincipal, IsSecretary

class ClassRoomViewSet(ModelViewSet):
    queryset = ClassRoom.objects.all().order_by("-created_at")
    serializer_class = ClassRoomSerializer
    permission_classes = [IsAuthenticated, (IsSecretary | IsStaffOrPrincipal)]
    pagination_class = StandardPagination

class CourseViewSet(ModelViewSet):
    queryset = Course.objects.all().order_by("name")
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated, (IsSecretary | IsStaffOrPrincipal)]

class TeacherCourseAssignmentViewSet(ModelViewSet):
    queryset = TeacherCourseAssignment.objects.select_related("teacher", "classroom", "course").all().order_by("-created_at")
    serializer_class = TeacherCourseAssignmentSerializer
    permission_classes = [IsAuthenticated, (IsSecretary | IsStaffOrPrincipal)]
    pagination_class = StandardPagination

class MonthlyGoalViewSet(ModelViewSet):
    queryset = MonthlyGoal.objects.select_related("classroom").all().order_by("-month", "-created_at")
    serializer_class = MonthlyGoalSerializer
    permission_classes = [IsAuthenticated, IsStaffOrPrincipal]
    pagination_class = StandardPagination
