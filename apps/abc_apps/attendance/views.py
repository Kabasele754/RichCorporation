# =========================
# apps/attendance/views.py
# =========================
from rest_framework.viewsets import ViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework import status

from commons.responses import ok, fail
from commons.permissions import IsStudent, IsTeacher
from apps.abc_apps.attendance.serializers import (
    StudentScanSerializer, TeacherScanSerializer, ConfirmSerializer,
    StudentAttendanceSerializer, TeacherCheckInSerializer, AttendanceConfirmationSerializer
)
from apps.abc_apps.attendance.services.scan import student_scan, teacher_scan, confirm_attendance
from apps.abc_apps.attendance.models import StudentAttendance

class AttendanceActionsViewSet(ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated, IsStudent])
    def student_scan(self, request):
        if not hasattr(request.user, "student_profile"):
            return fail("Student profile missing", status=404)

        ser = StudentScanSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            att, created = student_scan(ser.validated_data["qr_payload"], request.user.student_profile)
            return ok(StudentAttendanceSerializer(att).data, message="Attendance marked", status=200)
        except Exception as e:
            return fail(str(e), status=400)

    @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated, IsTeacher])
    def teacher_scan(self, request):
        if not hasattr(request.user, "teacher_profile"):
            return fail("Teacher profile missing", status=404)

        ser = TeacherScanSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            checkin = teacher_scan(ser.validated_data["qr_payload"], request.user.teacher_profile)
            return ok(TeacherCheckInSerializer(checkin).data, message="Teacher verified", status=200)
        except Exception as e:
            return fail(str(e), status=400)

    @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated, IsTeacher])
    def confirm(self, request):
        if not hasattr(request.user, "teacher_profile"):
            return fail("Teacher profile missing", status=404)

        ser = ConfirmSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            conf = confirm_attendance(
                session_id=ser.validated_data["session_id"],
                teacher=request.user.teacher_profile,
                notes=ser.validated_data.get("notes", ""),
            )
            return ok(AttendanceConfirmationSerializer(conf).data, message="Attendance confirmed", status=200)
        except Exception as e:
            return fail(str(e), status=400)

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated, IsTeacher])
    def session_list(self, request):
        session_id = request.query_params.get("session_id")
        if not session_id:
            return fail("session_id is required", status=400)

        qs = StudentAttendance.objects.select_related("student", "student__user").filter(session_id=session_id).order_by("student__student_code")
        data = StudentAttendanceSerializer(qs, many=True).data
        return ok(data)
