# apps/attendance/views.py
from datetime import date
from typing import Optional,Tuple
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




def _parse_client_time(value: Optional[str]) -> Optional[datetime]:
    """
    value = ISO string ex: '2026-02-18T08:42:10.123Z' ou sans Z.
    Retourne datetime aware (timezone) ou None.
    """
    if not value:
        return None

    s = str(value).strip()
    if not s:
        return None

    try:
        # Python datetime.fromisoformat ne supporte pas toujours 'Z'
        if s.endswith("Z"):
            s = s.replace("Z", "+00:00")

        dt = datetime.fromisoformat(s)

        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt, timezone.get_current_timezone())

        return dt

    except Exception:
        return None


def _compute_attendance_status(
    group,
    scan_dt: datetime,
    date_
) -> Tuple[str, Optional[int]]:
    """
    Retourne (status, late_by_minutes).

    - present si <= start_time + grace
    - late si > start_time + grace
    - si start_time absent => present
    """

    start_t = getattr(group, "start_time", None)
    grace = int(getattr(group, "late_grace_min", 45) or 45)

    if not start_t:
        return "present", None

    start_dt = datetime.combine(date_, start_t)
    start_dt = timezone.make_aware(
        start_dt,
        timezone.get_current_timezone()
    )

    diff_min = int((scan_dt - start_dt).total_seconds() / 60)

    # ✅ Si scan avant début ou dans la tolérance
    if diff_min <= grace:
        return "present", 0

    late_by = max(0, diff_min - grace)
    return "late", late_by
class StudentAttendanceViewSet(ViewSet):
    permission_classes = [IsAuthenticated, IsStudent]

    # =========================================================
    # 📚 CLASS ROOM SCAN
    # =========================================================
    @action(detail=False, methods=["post"], url_path="room-scan")
    def room_scan(self, request):
        """
        POST /api/student/attendance/room-scan/
        body:
          { "qr_data": "...", "lat": -26.2, "lng": 28.0, "client_time": "2026-02-18T08:42:00Z" }
        """
        student = request.user.student_profile
        qr_raw = (request.data.get("qr_data") or "").strip()
        if not qr_raw:
            return bad("qr_data is required", 400)

        # 1) Parse QR -> room_code
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

        # ✅ must match student's room
        if group.room_id != room.id:
            return bad("Wrong classroom", 403)

        # 2) GPS check (optional)
        lat = request.data.get("lat")
        lng = request.data.get("lng")
        if room.campus and lat is not None and lng is not None:
            try:
                lat_f = float(lat)
                lng_f = float(lng)
            except Exception:
                return bad("Invalid lat/lng", 400)

            if not is_within_campus(room.campus, lat_f, lng_f):
                return bad("Outside campus area", 403)
            request.user.set_location(lat_f, lng_f)

        # 3) Time source
        # Option A: serveur (default)
        server_scan_dt = timezone.now()

        # Option B (facultatif): client_time si présent et valide
        client_dt = _parse_client_time(request.data.get("client_time"))
        scan_dt = client_dt or server_scan_dt

        # 4) Compute status present/late
        status, late_by = _compute_attendance_status(group, scan_dt, today)

        with transaction.atomic():
            checkin, created = DailyRoomCheckIn.objects.get_or_create(
                period=period,
                date=today,
                room=room,
                student=student,
                defaults={
                    "monthly_group": group,
                    "status": status,
                    "scanned_by": "self_scan",
                    "required_confirmations": 3,
                    "scanned_at": scan_dt,
                }
            )

            if not created:
                # on met à jour à chaque scan (utile si un student re-scan)
                checkin.scanned_at = scan_dt
                checkin.status = status
                checkin.monthly_group = group
                checkin.save(update_fields=["scanned_at", "status", "monthly_group"])

        return ok(
            {
                "checkin": DailyRoomCheckInSerializer(checkin).data,
                "created": created,
                "qr_version": parsed.get("version"),
                "late_by_min": late_by,  # pratique côté UI toast
            },
            "Attendance saved ✅"
        )

    # =========================================================
    # 🧪 EXAM SCAN
    # =========================================================
    @action(detail=False, methods=["post"], url_path="scan-exam")
    def scan_exam(self, request):
        """
        POST /api/student/attendance/scan-exam/
        body: { "qr_data": "...", "course_id": 1, "lat": ..., "lng": ..., "client_time": "..." }
        """
        student = request.user.student_profile
        qr_raw = (request.data.get("qr_data") or "").strip()
        course_id = request.data.get("course_id", None)

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
            return bad("Not enrolled", 403)

        if not enroll.exam_unlock:
            return bad("Exam locked. Contact teacher.", 403)

        group = enroll.group
        if group.room_id != room.id:
            return bad("Wrong exam room", 403)

        # GPS optional
        lat = request.data.get("lat")
        lng = request.data.get("lng")
        if room.campus and lat is not None and lng is not None:
            try:
                lat_f = float(lat)
                lng_f = float(lng)
            except Exception:
                return bad("Invalid lat/lng", 400)

            if not is_within_campus(room.campus, lat_f, lng_f):
                return bad("Outside campus area", 403)

            request.user.set_location(lat_f, lng_f)

        # time source (same approach)
        server_scan_dt = timezone.now()
        client_dt = _parse_client_time(request.data.get("client_time"))
        scan_dt = client_dt or server_scan_dt

        entry, created = StudentExamEntry.objects.get_or_create(
            period=period,
            date=today,
            monthly_group=group,
            room=room,
            student=student,
            course_id=course_id,
            defaults={"scanned_at": scan_dt},
        )

        if not created and entry.scanned_at != scan_dt:
            entry.scanned_at = scan_dt
            entry.save(update_fields=["scanned_at"])

        return ok(
            {
                "exam_entry": StudentExamEntrySerializer(entry).data,
                "created": created,
                "group_id": group.id,
            },
            "Exam access granted ✅"
        )

    # =========================================================
    # 🔁 RE-ENROLL INTENT
    # =========================================================
    @action(detail=False, methods=["post"], url_path="reenroll-intent")
    def reenroll_intent(self, request):
        """
        POST /api/student/attendance/reenroll-intent/
        body: { "will_return": true/false, "reason": "" }
        """
        student = request.user.student_profile
        will_return = request.data.get("will_return", None)
        reason = (request.data.get("reason") or "").strip()

        if will_return is None:
            return bad("will_return is required", 400)

        # ✅ important: bool("false") == True in python -> fix it
        if isinstance(will_return, str):
            will_return = will_return.lower().strip() in ["1", "true", "yes", "y"]
        else:
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
    # 📜 HISTORY
    # =========================================================
    @action(detail=False, methods=["get"], url_path="history")
    def history(self, request):
        student = request.user.student_profile

        class_scans = DailyRoomCheckIn.objects.select_related(
            "period", "monthly_group", "room"
        ).filter(student=student).order_by("-date", "-scanned_at")

        exam_scans = StudentExamEntry.objects.select_related(
            "period", "monthly_group", "room"
        ).filter(student=student).order_by("-date", "-scanned_at")

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

