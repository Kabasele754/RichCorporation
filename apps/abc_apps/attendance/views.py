from datetime import datetime, timedelta
from typing import Optional, Tuple

from django.db import transaction
from django.utils import timezone

from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from apps.abc_apps.academics.models import (
    MonthlyClassGroup,
    Room,
    StudentMonthlyEnrollment,
    TeacherCourseAssignment,
    get_or_create_period_from_date,
)
from apps.abc_apps.accounts.views import bad
from apps.abc_apps.commons.responses import ok
from apps.common.permissions import IsStudent, IsTeacher

from .models import (
    DailyRoomCheckIn,
    DailyRoomCheckInApproval,
    StudentExamEntry,
    ReenrollmentIntent,
    TeacherCheckIn,
    RoomScanTag,
)
from .serializers import (
    DailyRoomCheckInSerializer,
    StudentExamEntrySerializer,
    ReenrollmentIntentSerializer,
    TeacherCheckInSerializer,
)

from .qr import parse_room_qr
from .geo import is_within_room_tag, is_within_campus


# =========================================================
# HELPERS
# =========================================================
def _parse_client_time(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    s = str(value).strip()
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt, timezone.get_current_timezone())
        return dt
    except Exception:
        return None


def _parse_client_ts(client_ts, tz_offset_min) -> Optional[datetime]:
    if client_ts in [None, ""]:
        return None
    try:
        ts_ms = int(client_ts)
    except Exception:
        return None

    dt_local_naive = datetime.fromtimestamp(ts_ms / 1000.0)

    try:
        off_min = int(tz_offset_min or 0)
    except Exception:
        off_min = 0

    offset = timezone.get_fixed_timezone(off_min)
    dt_local_aware = timezone.make_aware(dt_local_naive, offset)
    return dt_local_aware.astimezone(timezone.get_current_timezone())


def _compute_attendance_status(group, scan_dt: datetime, date_) -> Tuple[str, Optional[int]]:
    start_t = getattr(group, "start_time", None)
    grace = int(getattr(group, "late_grace_min", 45) or 45)

    if not start_t:
        return "present", None

    start_dt = timezone.make_aware(
        datetime.combine(date_, start_t),
        timezone.get_current_timezone(),
    )

    diff_min = int((scan_dt - start_dt).total_seconds() / 60)

    if diff_min <= grace:
        return "present", 0

    late_by = max(0, diff_min - grace)
    return "late", late_by


def _get_lat_lng(request):
    lat = request.data.get("lat")
    lng = request.data.get("lng")
    if lat is None or lng is None:
        return None, None, None, None
    try:
        lat_f = float(lat)
        lng_f = float(lng)
        return lat, lng, lat_f, lng_f
    except Exception:
        return lat, lng, None, None


def _load_room_and_tag(parsed_room_code: str, parsed_tag_id: Optional[str]):
    room = Room.objects.select_related("campus").filter(code=parsed_room_code).first()
    if not room:
        return None, None, "Room not found"

    tag = RoomScanTag.objects.filter(room=room, is_active=True).first()
    if not tag:
        return room, None, "Room tag not configured"

    if parsed_tag_id and str(tag.id) != str(parsed_tag_id):
        return room, tag, "Wrong tag for this room"

    return room, tag, None


def _resolve_scan_dt(request):
    server_scan_dt = timezone.now()

    client_dt = _parse_client_ts(
        request.data.get("client_ts"),
        request.data.get("tz_offset_min"),
    )

    if client_dt:
        delta_sec = abs((client_dt - server_scan_dt).total_seconds())
        if delta_sec > 5 * 60:
            client_dt = None

    scan_dt = client_dt or server_scan_dt
    return server_scan_dt, scan_dt


def _resolve_exam_scan_dt(request):
    server_scan_dt = timezone.now()
    client_dt = _parse_client_time(request.data.get("client_time"))
    scan_dt = client_dt or server_scan_dt
    return server_scan_dt, scan_dt


# =========================================================
# STUDENT
# =========================================================
class StudentAttendanceViewSet(ViewSet):
    permission_classes = [IsAuthenticated, IsStudent]

    # -----------------------------------------------------
    # Enrollment helper
    # -----------------------------------------------------
    def _get_active_enrollment(self, student, period):
        return (
            StudentMonthlyEnrollment.objects
            .select_related("group__room__campus")
            .filter(student=student, period=period, status="active")
            .first()
        )

    # -----------------------------------------------------
    # Save class attendance once only
    # -----------------------------------------------------
    def _save_room_attendance(
        self,
        *,
        request,
        student,
        room,
        tag,
        qr_raw: str,
        scan_medium: str,
        scan_dt: datetime,
        today,
        period,
        group,
        lat,
        lng,
        geo_ok: bool,
        distance_m,
        source: str = "scan",
    ):
        status_txt, late_by = _compute_attendance_status(group, scan_dt, today)

        with transaction.atomic():
            checkin, created = DailyRoomCheckIn.objects.get_or_create(
                period=period,
                date=today,
                room=room,
                student=student,
                defaults={
                    "monthly_group": group,
                    "status": status_txt,
                    "scanned_by": "self_scan",
                    "required_confirmations": 3,
                    "scanned_at": scan_dt,
                    "scan_medium": scan_medium,
                    "scan_payload": qr_raw,
                    "client_tz_offset_min": request.data.get("tz_offset_min"),
                    "client_latitude": lat,
                    "client_longitude": lng,
                    "distance_m": distance_m,
                    "geo_verified": bool(geo_ok),
                },
            )

            if created and hasattr(checkin, "source"):
                checkin.source = source
                checkin.save(update_fields=["source"])

            # ✅ if already exists: do NOT modify anything
            return checkin, created, late_by

    # -----------------------------------------------------
    # Save exam attendance once only per room/date/course
    # -----------------------------------------------------
    def _save_exam_entry(
        self,
        *,
        request,
        student,
        room,
        group,
        period,
        today,
        course_id,
        qr_raw,
        scan_medium,
        scan_dt,
        lat,
        lng,
        geo_ok,
        distance_m,
        source="scan",
    ):
        with transaction.atomic():
            entry, created = StudentExamEntry.objects.get_or_create(
                period=period,
                date=today,
                monthly_group=group,
                room=room,
                student=student,
                course_id=int(course_id) if course_id is not None else None,
                defaults={
                    "scanned_at": scan_dt,
                    "scan_medium": scan_medium,
                    "scan_payload": qr_raw,
                    "client_latitude": lat,
                    "client_longitude": lng,
                    "distance_m": distance_m,
                    "geo_verified": bool(geo_ok),
                },
            )

            if created and hasattr(entry, "source"):
                entry.source = source
                entry.save(update_fields=["source"])

            # ✅ if exists already: do NOT modify anything
            return entry, created

    # -----------------------------------------------------
    # Detect room by geo if room_code is unknown
    # -----------------------------------------------------
    def _find_room_tag_by_geo(self, *, lat_f: float, lng_f: float):
        matches = []

        tags = (
            RoomScanTag.objects
            .select_related("room__campus")
            .filter(is_active=True, room__is_active=True)
        )

        for tag in tags:
            room = tag.room
            campus = room.campus

            if campus:
                campus_ok, _, _ = is_within_campus(campus, lat_f, lng_f)
                if not campus_ok:
                    continue

            room_ok, dist_m, allowed_m = is_within_room_tag(tag, lat_f, lng_f)
            if room_ok:
                matches.append({
                    "tag": tag,
                    "room": room,
                    "distance_m": dist_m,
                    "allowed_m": allowed_m,
                })

        if not matches:
            return None, None, "No room found for current position"

        # sort nearest first
        matches.sort(key=lambda x: x["distance_m"] or 999999)

        if len(matches) > 1:
            first = matches[0]
            second = matches[1]
            # if too ambiguous, refuse
            if abs((first["distance_m"] or 0) - (second["distance_m"] or 0)) < 3:
                return None, None, "Multiple rooms match this position. Move closer to the correct room."

        best = matches[0]
        return best["room"], best["tag"], None

    # =====================================================
    # CLASS ROOM SCAN (QR / NFC)
    # =====================================================
    @action(detail=False, methods=["post"], url_path="room-scan")
    def room_scan(self, request):
        student = request.user.student_profile

        qr_raw = (request.data.get("qr_data") or "").strip()
        if not qr_raw:
            return bad("qr_data is required", 400)

        scan_medium = (request.data.get("scan_medium") or "qr").strip().lower()
        if scan_medium not in ["qr", "nfc"]:
            scan_medium = "qr"

        try:
            parsed = parse_room_qr(qr_raw)
        except ValueError as e:
            return bad(str(e), 400)

        room, tag, err = _load_room_and_tag(parsed["room_code"], parsed.get("tag_id"))
        if err:
            return bad(err, 403 if "tag" in err.lower() else 404)

        today = timezone.localdate()
        period = get_or_create_period_from_date(today)

        enroll = self._get_active_enrollment(student, period)
        if not enroll:
            return bad("Not enrolled this month", 403)

        group = enroll.group
        if group.room_id != room.id:
            return bad("Wrong classroom", 403)

        lat, lng, lat_f, lng_f = _get_lat_lng(request)
        if lat is None or lng is None:
            return bad("lat and lng are required for attendance scan", 400)
        if lat_f is None or lng_f is None:
            return bad("Invalid lat/lng", 400)

        if room.campus:
            campus_ok, campus_dist_m, campus_allowed_m = is_within_campus(
                room.campus, lat_f, lng_f
            )
            if not campus_ok:
                return bad(
                    f"Outside campus area ({campus_dist_m:.1f}m from center, allowed {campus_allowed_m:.1f}m).",
                    403,
                )

        geo_ok, distance_m, allowed_m = is_within_room_tag(tag, lat_f, lng_f)
        if not geo_ok:
            return bad(
                f"Too far from room tag ({distance_m:.1f}m). Allowed radius: {allowed_m:.1f}m",
                403,
            )

        request.user.set_location(lat_f, lng_f)

        server_scan_dt, scan_dt = _resolve_scan_dt(request)

        checkin, created, late_by = self._save_room_attendance(
            request=request,
            student=student,
            room=room,
            tag=tag,
            qr_raw=qr_raw,
            scan_medium=scan_medium,
            scan_dt=scan_dt,
            today=today,
            period=period,
            group=group,
            lat=lat,
            lng=lng,
            geo_ok=geo_ok,
            distance_m=distance_m,
            source="scan",
        )

        return ok(
            {
                "checkin": DailyRoomCheckInSerializer(checkin).data,
                "created": created,
                "already_recorded": not created,
                "qr_version": parsed.get("version"),
                "late_by_min": late_by,
                "distance_m": distance_m,
                "geo_verified": geo_ok,
                "server_ts": int(server_scan_dt.timestamp() * 1000),
                "client_ts_used": int(scan_dt.timestamp() * 1000),
            },
            "Attendance already recorded ✅" if not created else "Attendance saved ✅",
        )

    # =====================================================
    # CLASS AUTO GEO TARGET
    # =====================================================
    @action(detail=False, methods=["post"], url_path="room-geotarget-check")
    def room_geotarget_check(self, request):
        student = request.user.student_profile

        lat, lng, lat_f, lng_f = _get_lat_lng(request)
        if lat is None or lng is None:
            return bad("lat and lng are required", 400)
        if lat_f is None or lng_f is None:
            return bad("Invalid lat/lng", 400)

        today = timezone.localdate()
        period = get_or_create_period_from_date(today)

        enroll = self._get_active_enrollment(student, period)
        if not enroll:
            return bad("Not enrolled this month", 403)

        group = enroll.group
        room = group.room
        if not room:
            return bad("No classroom assigned", 403)

        tag = RoomScanTag.objects.filter(room=room, is_active=True).first()
        if not tag:
            return bad("Room tag not configured", 403)

        if room.campus:
            campus_ok, campus_dist_m, campus_allowed_m = is_within_campus(
                room.campus, lat_f, lng_f
            )
            if not campus_ok:
                return bad(
                    f"Outside campus area ({campus_dist_m:.1f}m from center, allowed {campus_allowed_m:.1f}m).",
                    403,
                )

        geo_ok, distance_m, allowed_m = is_within_room_tag(tag, lat_f, lng_f)
        if not geo_ok:
            return bad(
                f"You are not yet inside your classroom area ({distance_m:.1f}m away, allowed {allowed_m:.1f}m).",
                403,
            )

        request.user.set_location(lat_f, lng_f)

        _, scan_dt = _resolve_scan_dt(request)

        synthetic_payload = f"GEO_TARGET|ROOM|{room.code}|AUTO"

        checkin, created, late_by = self._save_room_attendance(
            request=request,
            student=student,
            room=room,
            tag=tag,
            qr_raw=synthetic_payload,
            scan_medium="geo",
            scan_dt=scan_dt,
            today=today,
            period=period,
            group=group,
            lat=str(lat),
            lng=str(lng),
            geo_ok=True,
            distance_m=distance_m,
            source="geo_target",
        )

        return ok(
            {
                "checkin": DailyRoomCheckInSerializer(checkin).data,
                "created": created,
                "already_recorded": not created,
                "late_by_min": late_by,
                "distance_m": distance_m,
                "geo_verified": True,
                "room_code": room.code,
                "room_name": room.name,
            },
            "Attendance already recorded ✅" if not created else "Auto attendance saved ✅",
        )

    # =====================================================
    # EXAM SCAN (QR / NFC)
    # =====================================================
    @action(detail=False, methods=["post"], url_path="scan-exam")
    def scan_exam(self, request):
        student = request.user.student_profile

        qr_raw = (request.data.get("qr_data") or "").strip()
        course_id = request.data.get("course_id", None)

        if not qr_raw:
            return bad("qr_data is required", 400)

        scan_medium = (request.data.get("scan_medium") or "qr").strip().lower()
        if scan_medium not in ["qr", "nfc"]:
            scan_medium = "qr"

        try:
            parsed = parse_room_qr(qr_raw)
        except ValueError as e:
            return bad(str(e), 400)

        room, tag, err = _load_room_and_tag(parsed["room_code"], parsed.get("tag_id"))
        if err:
            return bad(err, 403 if "tag" in err.lower() else 404)

        today = timezone.localdate()
        period = get_or_create_period_from_date(today)

        enroll = self._get_active_enrollment(student, period)
        if not enroll:
            return bad("Not enrolled", 403)

        # ✅ exam only if teacher/admin unlocked
        if not getattr(enroll, "exam_unlock", False):
            return bad("Exam not yet authorized. Wait for your teacher.", 403)

        group = enroll.group

        lat, lng, lat_f, lng_f = _get_lat_lng(request)
        if lat is None or lng is None:
            return bad("lat and lng are required for exam scan", 400)
        if lat_f is None or lng_f is None:
            return bad("Invalid lat/lng", 400)

        if room.campus:
            campus_ok, campus_dist_m, campus_allowed_m = is_within_campus(
                room.campus, lat_f, lng_f
            )
            if not campus_ok:
                return bad(
                    f"Outside campus area ({campus_dist_m:.1f}m from center, allowed {campus_allowed_m:.1f}m).",
                    403,
                )

        geo_ok, distance_m, allowed_m = is_within_room_tag(tag, lat_f, lng_f)
        if not geo_ok:
            return bad(
                f"Too far from exam room tag ({distance_m:.1f}m). Allowed radius: {allowed_m:.1f}m",
                403,
            )

        request.user.set_location(lat_f, lng_f)

        server_scan_dt, scan_dt = _resolve_exam_scan_dt(request)

        entry, created = self._save_exam_entry(
            request=request,
            student=student,
            room=room,
            group=group,
            period=period,
            today=today,
            course_id=course_id,
            qr_raw=qr_raw,
            scan_medium=scan_medium,
            scan_dt=scan_dt,
            lat=lat,
            lng=lng,
            geo_ok=geo_ok,
            distance_m=distance_m,
            source="scan",
        )

        return ok(
            {
                "exam_entry": StudentExamEntrySerializer(entry).data,
                "created": created,
                "already_recorded": not created,
                "group_id": group.id,
                "distance_m": distance_m,
                "geo_verified": geo_ok,
                "server_ts": int(server_scan_dt.timestamp() * 1000),
                "client_ts_used": int(scan_dt.timestamp() * 1000),
            },
            "Exam attendance already recorded ✅" if not created else "Exam access granted ✅",
        )

    # =====================================================
    # EXAM AUTO GEO TARGET
    # =====================================================
    @action(detail=False, methods=["post"], url_path="exam-geotarget-check")
    def exam_geotarget_check(self, request):
        """
        body:
        {
          "lat": ...,
          "lng": ...,
          "client_ts": ...,
          "tz_offset_min": ...,
          "room_code": "R7"   # optional
        }
        """
        student = request.user.student_profile
        room_code = (request.data.get("room_code") or "").strip()
        course_id = request.data.get("course_id", None)

        lat, lng, lat_f, lng_f = _get_lat_lng(request)
        if lat is None or lng is None:
            return bad("lat and lng are required", 400)
        if lat_f is None or lng_f is None:
            return bad("Invalid lat/lng", 400)

        today = timezone.localdate()
        period = get_or_create_period_from_date(today)

        enroll = self._get_active_enrollment(student, period)
        if not enroll:
            return bad("Not enrolled", 403)

        if not getattr(enroll, "exam_unlock", False):
            return bad("Exam not yet authorized. Wait for your teacher.", 403)

        group = enroll.group

        room = None
        tag = None

        if room_code:
            room = Room.objects.select_related("campus").filter(code=room_code).first()
            if not room:
                return bad("Room not found", 404)

            tag = RoomScanTag.objects.filter(room=room, is_active=True).first()
            if not tag:
                return bad("Room tag not configured", 403)
        else:
            room, tag, err = self._find_room_tag_by_geo(lat_f=lat_f, lng_f=lng_f)
            if err:
                return bad(err, 403)

        if room.campus:
            campus_ok, campus_dist_m, campus_allowed_m = is_within_campus(
                room.campus, lat_f, lng_f
            )
            if not campus_ok:
                return bad(
                    f"Outside campus area ({campus_dist_m:.1f}m from center, allowed {campus_allowed_m:.1f}m).",
                    403,
                )

        geo_ok, distance_m, allowed_m = is_within_room_tag(tag, lat_f, lng_f)
        if not geo_ok:
            return bad(
                f"You are not yet inside the exam room area ({distance_m:.1f}m away, allowed {allowed_m:.1f}m).",
                403,
            )

        request.user.set_location(lat_f, lng_f)

        _, scan_dt = _resolve_scan_dt(request)

        synthetic_payload = f"GEO_TARGET|EXAM|{room.code}|AUTO"

        entry, created = self._save_exam_entry(
            request=request,
            student=student,
            room=room,
            group=group,
            period=period,
            today=today,
            course_id=course_id,
            qr_raw=synthetic_payload,
            scan_medium="geo",
            scan_dt=scan_dt,
            lat=str(lat),
            lng=str(lng),
            geo_ok=True,
            distance_m=distance_m,
            source="geo_target",
        )

        return ok(
            {
                "exam_entry": StudentExamEntrySerializer(entry).data,
                "created": created,
                "already_recorded": not created,
                "group_id": group.id,
                "room_code": room.code,
                "room_name": room.name,
                "distance_m": distance_m,
                "geo_verified": True,
            },
            "Exam attendance already recorded ✅" if not created else "Exam auto attendance saved ✅",
        )

    # =====================================================
    # RE-ENROLL INTENT
    # =====================================================
    @action(detail=False, methods=["post"], url_path="reenroll-intent")
    def reenroll_intent(self, request):
        student = request.user.student_profile
        will_return = request.data.get("will_return", None)
        reason = (request.data.get("reason") or "").strip()

        if will_return is None:
            return bad("will_return is required", 400)

        if isinstance(will_return, str):
            will_return = will_return.lower().strip() in ["1", "true", "yes", "y"]
        else:
            will_return = bool(will_return)

        today = timezone.localdate()
        from_period = get_or_create_period_from_date(today)
        to_period = get_or_create_period_from_date(from_period.start_date + timedelta(days=32))

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
            "Reenrollment saved ✅",
        )

    # =====================================================
    # HISTORY
    # =====================================================
    @action(detail=False, methods=["get"], url_path="history")
    def history(self, request):
        student = request.user.student_profile

        class_scans = (
            DailyRoomCheckIn.objects
            .select_related("period", "monthly_group", "room")
            .filter(student=student)
            .order_by("-date", "-scanned_at")
        )

        exam_scans = (
            StudentExamEntry.objects
            .select_related("period", "monthly_group", "room")
            .filter(student=student)
            .order_by("-date", "-scanned_at")
        )

        return ok(
            {
                "class_scans": DailyRoomCheckInSerializer(class_scans, many=True).data,
                "exam_scans": StudentExamEntrySerializer(exam_scans, many=True).data,
            },
            "History",
        )      
        
class TeacherAttendanceViewSet(ViewSet):
    """
    ✅ Teacher scan QR/NFC pour prouver présence (geo room).
    Ensuite ils confirment les students via l'endpoint confirm.
    """
    permission_classes = [IsAuthenticated, IsTeacher]

    @action(detail=False, methods=["post"], url_path="teacher-scan")
    def teacher_scan(self, request):
        """
        POST /api/teacher/attendance/teacher-scan/
        body:
        {
          "qr_data": "ABCR|ROOM|R7|tag_uuid|sig",
          "scan_medium": "qr" | "nfc",
          "lat": ..., "lng": ...,
          "client_ts": ..., "tz_offset_min": ...
        }
        """
        teacher = request.user.teacher_profile
        qr_raw = (request.data.get("qr_data") or "").strip()
        if not qr_raw:
            return bad("qr_data is required", 400)

        scan_medium = (request.data.get("scan_medium") or "qr").strip().lower()
        if scan_medium not in ["qr", "nfc"]:
            scan_medium = "qr"

        try:
            parsed = parse_room_qr(qr_raw)
        except ValueError as e:
            return bad(str(e), 400)

        room, tag, err = _load_room_and_tag(parsed["room_code"], parsed.get("tag_id"))
        if err:
            return bad(err, 403 if "tag" in err.lower() else 404)

        today = timezone.localdate()
        period = get_or_create_period_from_date(today)

        # ✅ teacher doit être assigné à un group dans cette room ce jour/period
        allowed_groups = TeacherCourseAssignment.objects.filter(
            teacher=teacher,
            monthly_group__period=period,
            monthly_group__room=room,
        ).values_list("monthly_group_id", flat=True)

        allowed_groups = list(allowed_groups)
        if not allowed_groups:
            return bad("Not assigned to this room (this period)", 403)

        # choix du group: si l’app envoie group_id -> utilise; sinon premier
        group_id = request.data.get("group_id")
        if group_id:
            try:
                gid = int(group_id)
            except Exception:
                return bad("Invalid group_id", 400)
            if gid not in set(allowed_groups):
                return bad("Not allowed for this group", 403)
            group = MonthlyClassGroup.objects.filter(id=gid).first()
        else:
            group = MonthlyClassGroup.objects.filter(id=allowed_groups[0]).first()

        if not group:
            return bad("Group not found", 404)

        # GEO checks
        lat, lng, lat_f, lng_f = _get_lat_lng(request)
        geo_ok = True
        distance_m = None

        if lat is not None and lng is not None:
            if lat_f is None or lng_f is None:
                return bad("Invalid lat/lng", 400)

            if room.campus and not is_within_campus(room.campus, lat_f, lng_f):
                return bad("Outside campus area", 403)

            geo_ok, distance_m = is_within_room_tag(tag, lat_f, lng_f)
            if not geo_ok:
                return bad(f"Too far from room tag ({distance_m:.1f}m)", 403)

            request.user.set_location(lat_f, lng_f)

        # time source
        server_scan_dt = timezone.now()
        client_dt = _parse_client_ts(request.data.get("client_ts"), request.data.get("tz_offset_min"))
        if client_dt:
            delta_sec = abs((client_dt - server_scan_dt).total_seconds())
            if delta_sec > 5 * 60:
                client_dt = None
        scan_dt = client_dt or server_scan_dt

        # save / upsert teacher checkin
        checkin, created = TeacherCheckIn.objects.get_or_create(
            session=group,
            teacher=teacher,
            defaults={"scanned_at": scan_dt, "verified": bool(geo_ok)},
        )
        checkin.scanned_at = scan_dt
        checkin.verified = bool(geo_ok)

        checkin.scan_medium = scan_medium
        checkin.scan_payload = qr_raw
        checkin.client_latitude = lat
        checkin.client_longitude = lng
        checkin.distance_m = distance_m
        checkin.save()

        return ok(
            {
                "teacher_checkin": TeacherCheckInSerializer(checkin).data,
                "created": created,
                "geo_verified": geo_ok,
                "distance_m": distance_m,
            },
            "Teacher check-in saved ✅"
        )


class TeacherAttendanceConfirmViewSet(ViewSet):
    permission_classes = [IsAuthenticated, IsTeacher]

    @action(detail=False, methods=["post"], url_path="confirm")
    def confirm(self, request):
        teacher = request.user.teacher_profile
        checkin_id = request.data.get("checkin_id")
        approved = request.data.get("approved", True)
        note = (request.data.get("note") or "").strip()

        if not checkin_id:
            return bad("checkin_id required", 400)

        # bool safety
        if isinstance(approved, str):
            approved = approved.lower().strip() in ["1", "true", "yes", "y"]
        else:
            approved = bool(approved)

        checkin = DailyRoomCheckIn.objects.select_related("monthly_group").filter(id=checkin_id).first()
        if not checkin:
            return bad("Not found", 404)

        # teacher allowed groups
        allowed = TeacherCourseAssignment.objects.filter(teacher=teacher)\
            .values_list("monthly_group_id", flat=True)
        if checkin.monthly_group_id not in set(allowed):
            return bad("Not allowed", 403)

        approval, _ = DailyRoomCheckInApproval.objects.update_or_create(
            checkin=checkin,
            teacher=teacher,
            defaults={
                "approved": approved,
                "note": note,
                "decided_at": timezone.now(),
            }
        )

        checkin.refresh_from_db()

        return ok({
            "checkin": DailyRoomCheckInSerializer(checkin).data,
            "teacher_approval": {
                "approved": approval.approved,
                "note": approval.note,
            }
        }, "Confirmation saved ✅")

    @action(detail=False, methods=["get"], url_path="pending")
    def pending(self, request):
        teacher = request.user.teacher_profile
        group_id = request.query_params.get("group_id")
        d = request.query_params.get("date")

        qs = DailyRoomCheckIn.objects.select_related("period", "monthly_group", "room", "student__user")\
            .prefetch_related("approvals", "approvals__teacher__user")

        allowed = TeacherCourseAssignment.objects.filter(teacher=teacher)\
            .values_list("monthly_group_id", flat=True)
        qs = qs.filter(monthly_group_id__in=allowed)

        if group_id:
            qs = qs.filter(monthly_group_id=group_id)
        if d:
            qs = qs.filter(date=d)
        else:
            qs = qs.filter(date=timezone.localdate())

        qs = [c for c in qs.order_by("-scanned_at") if not c.is_fully_confirmed]
        return ok({"items": DailyRoomCheckInSerializer(qs, many=True).data}, "Pending confirmations")