# apps/attendance/views.py
from datetime import date
from datetime import timedelta, datetime
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework.response import Response

from apps.abc_apps.academics.models import MonthlyClassGroup, Room, StudentMonthlyEnrollment, TeacherCourseAssignment, get_or_create_period_from_date
from apps.abc_apps.accounts.views import bad
from apps.abc_apps.attendance.time_qr import compute_status
from apps.abc_apps.commons.period_utils import next_month
from apps.abc_apps.commons.responses import ok
from apps.common.permissions import IsStudent, IsTeacher
from .models import DailyRoomCheckIn, DailyRoomCheckInApproval, StudentExamEntry, ReenrollmentIntent
from .serializers import DailyRoomCheckInSerializer, StudentExamEntrySerializer, ReenrollmentIntentSerializer


from apps.abc_apps.attendance.qr import parse_group_qr, parse_room_qr
from apps.abc_apps.attendance.geo import is_within_campus




class StudentAttendanceViewSet(ViewSet):
    permission_classes = [IsAuthenticated, IsStudent]

    # =========================================================
    # 📚 CLASS ROOM SCAN
    # =========================================================
    
    @action(detail=False, methods=["post"], url_path="room-scan")
    def room_scan(self, request):
        student = request.user.student_profile
        qr_raw = (request.data.get("qr_data") or "").strip()
        if not qr_raw:
            return bad("qr_data is required", 400)

        try:
            parsed = parse_room_qr(qr_raw)
        except ValueError as e:
            return bad(str(e), 400)

        room = Room.objects.select_related("campus").filter(code=parsed["room_code"]).first()
        if not room:
            return bad("Room not found", 404)

        today = timezone.localdate()
        period = get_or_create_period_from_date(today)

        enroll = (
            StudentMonthlyEnrollment.objects
            .select_related("group__room")
            .filter(student=student, period=period, status="active")
            .first()
        )
        if not enroll:
            return bad("Not enrolled this month", 403)

        group = enroll.group
        if group.room_id != room.id:
            return bad("Wrong classroom", 403)

        # ✅ read client time (optional)
        client_ts = request.data.get("client_ts")  # epoch ms
        client_dt = None
        client_offset = request.data.get("tz_offset_min")  # ex: 120
        try:
            if client_ts is not None:
                client_dt = datetime.fromtimestamp(int(client_ts) / 1000.0, tz=timezone.get_current_timezone())
        except Exception:
            client_dt = None

        # ✅ GPS check (comme tu as déjà)
        lat = request.data.get("lat")
        lng = request.data.get("lng")
        if room.campus and lat and lng:
            if not is_within_campus(room.campus, float(lat), float(lng)):
                return bad("Outside campus area", 403)
            request.user.set_location(float(lat), float(lng))

        server_dt = timezone.now()
        status = compute_status(group, today, server_dt, client_dt)

        checkin, created = DailyRoomCheckIn.objects.get_or_create(
            period=period,
            date=today,
            monthly_group=group,
            room=room,
            student=student,
            defaults={
                "status": status,
                "scanned_by": "self_scan",
                "required_confirmations": 3,
                "scanned_at": server_dt,
                "client_scanned_at": client_dt,
                "client_tz_offset_min": int(client_offset) if client_offset is not None else None,
            }
        )

        # si déjà existant: tu peux mettre à jour le status/scanned_at
        if not created:
            checkin.scanned_at = server_dt
            checkin.status = status
            checkin.client_scanned_at = client_dt
            checkin.client_tz_offset_min = int(client_offset) if client_offset is not None else None
            checkin.save(update_fields=["scanned_at","status","client_scanned_at","client_tz_offset_min"])

        return ok(
            {"checkin": DailyRoomCheckInSerializer(checkin).data, "created": created},
            "Attendance saved ✅"
        )
    # @action(detail=False, methods=["post"], url_path="room-scan")
    # def room_scan(self, request):

    #     student = request.user.student_profile
    #     qr_raw = (request.data.get("qr_data") or "").strip()

    #     if not qr_raw:
    #         return bad("qr_data is required", 400)

    #     try:
    #         parsed = parse_room_qr(qr_raw)
    #     except ValueError as e:
    #         return bad(str(e), 400)

    #     room = Room.objects.select_related("campus").filter(
    #         code=parsed["room_code"]
    #     ).first()

    #     if not room:
    #         return bad("Room not found", 404)

    #     today = timezone.localdate()
    #     period = get_or_create_period_from_date(today)

    #     enroll = (
    #         StudentMonthlyEnrollment.objects
    #         .select_related("group__room")
    #         .filter(student=student, period=period, status="active")
    #         .first()
    #     )

    #     if not enroll:
    #         return bad("Not enrolled this month", 403)

    #     group = enroll.group

    #     if group.room_id != room.id:
    #         return bad("Wrong classroom", 403)

    #     # ✅ GPS check
    #     lat = request.data.get("lat")
    #     lng = request.data.get("lng")

    #     if room.campus and lat and lng:
    #         if not is_within_campus(room.campus, float(lat), float(lng)):
    #             return bad("Outside campus area", 403)
    #         request.user.set_location(float(lat), float(lng))

    #     checkin, created = DailyRoomCheckIn.objects.get_or_create(
    #         period=period,
    #         date=today,
    #         monthly_group=group,
    #         room=room,
    #         student=student,
    #         defaults={
    #             "status": "present",
    #             "scanned_by": "self_scan",
    #             "required_confirmations": 3,
    #         }
    #     )

    #     return ok(
    #         {
    #             "checkin": DailyRoomCheckInSerializer(checkin).data,
    #             "created": created,
    #         },
    #         "Attendance saved ✅"
    #     )

    # =========================================================
    # 🧪 EXAM SCAN
    # =========================================================
    @action(detail=False, methods=["post"], url_path="scan-exam")
    def scan_exam(self, request):

        student = request.user.student_profile
        qr_raw = (request.data.get("qr_data") or "").strip()
        course_id = request.data.get("course_id")

        if not qr_raw:
            return bad("qr_data is required", 400)

        try:
            parsed = parse_room_qr(qr_raw)
        except ValueError as e:
            return bad(str(e), 400)

        room = Room.objects.select_related("campus").filter(
            code=parsed["room_code"]
        ).first()

        if not room:
            return bad("Room not found", 404)

        today = timezone.localdate()
        period = get_or_create_period_from_date(today)

        enroll = (
            StudentMonthlyEnrollment.objects
            .select_related("group__room")
            .filter(student=student, period=period, status="active")
            .first()
        )

        if not enroll:
            return bad("Not enrolled", 403)

        if not enroll.exam_unlock:
            return bad("Exam locked. Contact teacher.", 403)

        group = enroll.group

        if group.room_id != room.id:
            return bad("Wrong exam room", 403)

        # ✅ GPS security
        lat = request.data.get("lat")
        lng = request.data.get("lng")

        if room.campus and lat and lng:
            if not is_within_campus(room.campus, float(lat), float(lng)):
                return bad("Outside campus area", 403)
            request.user.set_location(float(lat), float(lng))

        entry, created = StudentExamEntry.objects.get_or_create(
            period=period,
            date=today,
            monthly_group=group,
            room=room,
            student=student,
            course_id=course_id,
        )

        return ok(
            {
                "exam_entry": StudentExamEntrySerializer(entry).data,
                "created": created,
                "group_id": group.id,
            },
            "Exam access granted ✅"
        )

    # =========================================================
    # 🔁 RE-ENROLL INTENT (après exam)
    # =========================================================
    @action(detail=False, methods=["post"], url_path="reenroll-intent")
    def reenroll_intent(self, request):

        student = request.user.student_profile
        will_return = request.data.get("will_return")
        reason = (request.data.get("reason") or "").strip()

        if will_return is None:
            return bad("will_return is required", 400)

        will_return = bool(will_return)

        today = timezone.localdate()
        from_period = get_or_create_period_from_date(today)
        to_period = get_or_create_period_from_date(next_month(today))

        current = (
            StudentMonthlyEnrollment.objects
            .select_related("group")
            .filter(student=student, period=from_period)
            .first()
        )

        if not current:
            return bad("No current enrollment", 403)

        with transaction.atomic():

            intent, _ = ReenrollmentIntent.objects.update_or_create(
                student=student,
                to_period=to_period,
                defaults={
                    "from_period": from_period,
                    "will_return": will_return,
                    "reason": reason,
                    "status": "pending",
                },
            )

            next_enroll_id = None

            if will_return:
                next_enroll, _ = StudentMonthlyEnrollment.objects.get_or_create(
                    student=student,
                    period=to_period,
                    group=current.group,
                    defaults={"status": "pending"},
                )
                next_enroll_id = next_enroll.id

        return ok(
            {
                "intent": ReenrollmentIntentSerializer(intent).data,
                "pending_enrollment_id": next_enroll_id,
            },
            "Reenrollment saved ✅"
        )

    # =========================================================
    # 📜 HISTORY (CLASS + EXAM)
    # =========================================================
    @action(detail=False, methods=["get"], url_path="history")
    def history(self, request):

        student = request.user.student_profile

        class_scans = DailyRoomCheckIn.objects.filter(
            student=student
        ).order_by("-date")

        exam_scans = StudentExamEntry.objects.filter(
            student=student
        ).order_by("-date")

        return ok(
            {
                "class_scans": DailyRoomCheckInSerializer(class_scans, many=True).data,
                "exam_scans": StudentExamEntrySerializer(exam_scans, many=True).data,
            },
            "History"
        )
        

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
    def scan_exam(self, request):
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
    def reenroll_intent(self, request):
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

