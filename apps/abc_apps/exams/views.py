# =========================
# apps/exams/views.py
# =========================
from django.utils import timezone
from rest_framework.viewsets import ModelViewSet, ViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action

from commons.responses import ok, fail
from commons.permissions import IsTeacher, IsStudent
from apps.abc_apps.sessions_abc.services.qr import validate_payload
from apps.abc_apps.exams.models import ExamRuleStatus, ExamEntryScan, MonthlyReturnForm
from apps.abc_apps.exams.serializers import (
    ExamRuleStatusSerializer, ExamEntryScanSerializer,
    ExamEntryScanRequestSerializer, ReturnFormRequestSerializer, MonthlyReturnFormSerializer
)
from apps.abc_apps.exams.services.eligibility import check_student_eligibility

class ExamRuleStatusViewSet(ModelViewSet):
    queryset = ExamRuleStatus.objects.select_related("student", "classroom").all().order_by("-updated_at")
    serializer_class = ExamRuleStatusSerializer
    permission_classes = [IsAuthenticated, IsTeacher]

class ExamActionsViewSet(ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated, IsStudent])
    def entry_scan(self, request):
        if not hasattr(request.user, "student_profile"):
            return fail("Student profile missing", status=404)

        ser = ExamEntryScanRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            token = validate_payload(ser.validated_data["qr_payload"])
            session = token.session
            if session.session_type != "exam":
                return fail("This is not an exam session", status=400)

            student = request.user.student_profile
            allowed, reason = check_student_eligibility(student.id, session.classroom_id)

            scan, _ = ExamEntryScan.objects.get_or_create(
                session=session,
                student=student,
                defaults={"scanned_at": timezone.now(), "allowed": allowed, "reason": reason},
            )
            # update on repeat scan
            scan.allowed = allowed
            scan.reason = reason
            scan.save(update_fields=["allowed", "reason"])

            return ok(ExamEntryScanSerializer(scan).data, message="Scan processed")
        except Exception as e:
            return fail(str(e), status=400)

    @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated, IsStudent])
    def return_form(self, request):
        if not hasattr(request.user, "student_profile"):
            return fail("Student profile missing", status=404)

        ser = ReturnFormRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        student = request.user.student_profile
        form, _ = MonthlyReturnForm.objects.get_or_create(
            student=student,
            month=ser.validated_data["month"],
            defaults={
                "will_return": ser.validated_data["will_return"],
                "reason_if_no": ser.validated_data.get("reason_if_no", ""),
                "submitted_at": timezone.now(),
            },
        )
        # allow update
        form.will_return = ser.validated_data["will_return"]
        form.reason_if_no = ser.validated_data.get("reason_if_no", "")
        form.save(update_fields=["will_return", "reason_if_no"])

        return ok(MonthlyReturnFormSerializer(form).data, message="Return form saved")
