# apps/attendance/views.py
from datetime import date
from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework.response import Response

from apps.abc_apps.academics.models import MonthlyClassGroup, StudentMonthlyEnrollment, TeacherCourseAssignment, get_or_create_period_from_date
from apps.abc_apps.accounts.views import bad
from apps.abc_apps.commons.responses import ok
from apps.common.permissions import IsStudent, IsTeacher
from .models import DailyRoomCheckIn, DailyRoomCheckInApproval, StudentExamEntry, ReenrollmentIntent
from .serializers import DailyRoomCheckInSerializer, StudentExamEntrySerializer, ReenrollmentIntentSerializer
from .qr import parse_group_qr


class StudentAttendanceViewSet(ViewSet):
    permission_classes = [IsAuthenticated, IsStudent]

    @action(detail=False, methods=["post"])
    def scan_door(self, request):
        """
        POST /api/student/attendance/scan-door/
        body: { "qr_data": "GROUP:12" }
        """
        student = request.user.student_profile
        qr_data = request.data.get("qr_data")

        try:
            parsed = parse_group_qr(qr_data)
        except ValueError as e:
            return bad(str(e), status_code=400)

        group = MonthlyClassGroup.objects.select_related("period", "room").filter(id=parsed["group_id"]).first()
        if not group:
            return bad("Invalid group", status_code=400)

        today = timezone.localdate()

        # ✅ l’étudiant doit être enrollé dans CE group / CE period
        enrollment = StudentMonthlyEnrollment.objects.filter(
            period=group.period,
            student=student,
            group=group,
            status__in=["active", "pending"],  # tu peux limiter à active seulement si tu veux
        ).first()
        if not enrollment:
            return bad("Not enrolled in this class group for this period.", status_code=403)

        with transaction.atomic():
            checkin, created = DailyRoomCheckIn.objects.get_or_create(
                period=group.period,
                date=today,
                monthly_group=group,
                room=group.room,
                student=student,
                defaults={
                    "scanned_at": timezone.now(),
                    "status": "present",
                    "scanned_by": "self_scan",
                    "required_confirmations": 3,
                }
            )

            if not created:
                # update scanned_at to latest scan if you want
                checkin.scanned_at = timezone.now()
                checkin.save(update_fields=["scanned_at"])

        return ok(
            data={
                "checkin": DailyRoomCheckInSerializer(checkin).data,
                "created": created,
                "qr_version": parsed["version"],
            },
            message="Check-in saved ✅"
        )

    @action(detail=False, methods=["get"])
    def my_today(self, request):
        student = request.user.student_profile
        today = timezone.localdate()

        qs = DailyRoomCheckIn.objects.select_related("period", "monthly_group", "room", "student__user")\
            .prefetch_related("approvals", "approvals__teacher__user")\
            .filter(student=student, date=today)\
            .order_by("-scanned_at")

        return ok({"items": DailyRoomCheckInSerializer(qs, many=True).data}, "My today check-ins")


class TeacherAttendanceConfirmViewSet(ViewSet):
    permission_classes = [IsAuthenticated, IsTeacher]

    @action(detail=False, methods=["post"])
    def confirm(self, request):
        """
        POST /api/teacher/attendance/confirm/
        body: { "checkin_id": 123, "approved": true, "note": "" }
        """
        teacher = request.user.teacher_profile
        checkin_id = request.data.get("checkin_id")
        approved = bool(request.data.get("approved", True))
        note = (request.data.get("note") or "").strip()

        if not checkin_id:
            return bad("checkin_id required")

        checkin = DailyRoomCheckIn.objects.select_related("monthly_group").filter(id=checkin_id).first()
        if not checkin:
            return bad("Not found", status_code=404)

        # ✅ security: teacher must be assigned to that monthly_group
        allowed = TeacherCourseAssignment.objects.filter(teacher=teacher)\
            .values_list("monthly_group_id", flat=True)
        if checkin.monthly_group_id not in set(allowed):
            return bad("Not allowed", status_code=403)

        approval, _ = DailyRoomCheckInApproval.objects.update_or_create(
            checkin=checkin,
            teacher=teacher,
            defaults={
                "approved": approved,
                "note": note,
                "decided_at": timezone.now(),
            }
        )

        # reload counts
        checkin.refresh_from_db()

        return ok({
            "checkin": DailyRoomCheckInSerializer(checkin).data,
            "teacher_approval": {
                "approved": approval.approved,
                "note": approval.note,
            }
        }, "Confirmation saved ✅")

    @action(detail=False, methods=["get"])
    def pending(self, request):
        """
        GET /api/teacher/attendance/pending/?group_id=12&date=YYYY-MM-DD
        -> retourne les checkins à confirmer (approvals_count < 3)
        """
        teacher = request.user.teacher_profile
        group_id = request.query_params.get("group_id")
        d = request.query_params.get("date")

        qs = DailyRoomCheckIn.objects.select_related("period", "monthly_group", "room", "student__user")\
            .prefetch_related("approvals", "approvals__teacher__user")

        # teacher allowed groups
        allowed = TeacherCourseAssignment.objects.filter(teacher=teacher)\
            .values_list("monthly_group_id", flat=True)
        qs = qs.filter(monthly_group_id__in=allowed)

        if group_id:
            qs = qs.filter(monthly_group_id=group_id)
        if d:
            qs = qs.filter(date=d)
        else:
            qs = qs.filter(date=timezone.localdate())

        # only not fully confirmed
        qs = [c for c in qs.order_by("-scanned_at") if not c.is_fully_confirmed]

        return ok({"items": DailyRoomCheckInSerializer(qs, many=True).data}, "Pending confirmations")


class StudentExamViewSet(ViewSet):
    permission_classes = [IsAuthenticated, IsStudent]

    @action(detail=False, methods=["post"])
    def scan_entry(self, request):
        """
        POST /api/student/exam/scan-entry/
        body: { "qr_data": "GROUP:12", "course_id": 4 }
        """
        student = request.user.student_profile
        qr_data = request.data.get("qr_data")
        course_id = request.data.get("course_id")  # optionnel

        try:
            parsed = parse_group_qr(qr_data)
        except ValueError as e:
            return bad(str(e), 400)

        group = MonthlyClassGroup.objects.select_related("period", "room").filter(id=parsed["group_id"]).first()
        if not group:
            return bad("Invalid group", 400)

        # ✅ must be enrolled
        enrollment = StudentMonthlyEnrollment.objects.filter(
            period=group.period,
            student=student,
            group=group,
            status="active",
        ).first()
        if not enrollment:
            return bad("Not enrolled (active) in this group.", 403)

        # ✅ must be unlocked by teachers
        if not enrollment.exam_unlock:
            return bad("Exam not unlocked for you yet.", 403)

        today = timezone.localdate()

        entry, created = StudentExamEntry.objects.get_or_create(
            period=group.period,
            date=today,
            monthly_group=group,
            room=group.room,
            student=student,
            course_id=int(course_id) if course_id is not None else None,
            defaults={"scanned_at": timezone.now()},
        )

        if not created:
            entry.scanned_at = timezone.now()
            entry.save(update_fields=["scanned_at"])

        return ok({"entry": StudentExamEntrySerializer(entry).data, "created": created}, "Exam entry OK ✅")




class StudentReenrollmentViewSet(ViewSet):
    permission_classes = [IsAuthenticated, IsStudent]

    @action(detail=False, methods=["post"])
    def request(self, request):
        """
        POST /api/student/reenroll/request/
        body: { "group_id": 12, "will_return": true, "reason": "" }
        """
        student = request.user.student_profile
        group_id = request.data.get("group_id")
        will_return = bool(request.data.get("will_return", False))
        reason = (request.data.get("reason") or "").strip()

        group = MonthlyClassGroup.objects.select_related("period", "room", "level").filter(id=group_id).first()
        if not group:
            return bad("Invalid group", 400)

        # student must have been enrolled this period (active or pending)
        current = StudentMonthlyEnrollment.objects.filter(
            period=group.period, student=student, group=group
        ).first()
        if not current:
            return bad("You are not enrolled in this group for this period.", 403)

        # next period (ex: + 32 days -> next month)
        next_period = get_or_create_period_from_date(group.period.start_date + timedelta(days=32))

        intent, _ = ReenrollmentIntent.objects.update_or_create(
            student=student,
            to_period=next_period,
            defaults={
                "from_period": group.period,
                "will_return": will_return,
                "reason": reason,
                "status": "pending",
            }
        )

        created_enrollment = None
        if will_return:
            # ✅ auto enrollment next period, status=pending
            # Option: même level+group_name+room -> on cherche un MonthlyClassGroup du prochain period
            next_group = MonthlyClassGroup.objects.filter(
                period=next_period,
                level=group.level,
                group_name=group.group_name,
                room=group.room,
            ).first()

            if next_group:
                enr, _ = StudentMonthlyEnrollment.objects.get_or_create(
                    period=next_period,
                    student=student,
                    group=next_group,
                    defaults={"status": "pending"}
                )
                created_enrollment = enr.id

        return ok(
            {
                "intent": ReenrollmentIntentSerializer(intent).data,
                "pending_enrollment_id": created_enrollment,
            },
            "Reenrollment request saved ✅"
        )

