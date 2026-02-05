# =========================
# apps/feedback/views.py
# =========================
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from commons.permissions import IsTeacher, IsStaffOrPrincipal
from apps.abc_apps.feedback.models import TeacherRemark, MonthlyStudentReport
from apps.abc_apps.feedback.serializers import TeacherRemarkSerializer, MonthlyStudentReportSerializer

class TeacherRemarkViewSet(ModelViewSet):
    queryset = TeacherRemark.objects.select_related("student", "teacher").all().order_by("-created_at")
    serializer_class = TeacherRemarkSerializer
    permission_classes = [IsAuthenticated, IsTeacher]

    def perform_create(self, serializer):
        serializer.save(teacher=self.request.user.teacher_profile)

class MonthlyStudentReportViewSet(ModelViewSet):
    queryset = MonthlyStudentReport.objects.select_related("student", "created_by").all().order_by("-month", "-created_at")
    serializer_class = MonthlyStudentReportSerializer
    permission_classes = [IsAuthenticated, IsStaffOrPrincipal]
