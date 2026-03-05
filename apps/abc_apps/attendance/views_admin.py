import base64
from io import BytesIO

import qrcode
from django.db import transaction
from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from apps.abc_apps.accounts.views import bad
from apps.abc_apps.commons.responses import ok

from apps.abc_apps.academics.models import Room, SchoolCampus
from apps.abc_apps.attendance.geo import is_within_campus
from apps.common.permissions import IsSecretary
from apps.common.permissions import IsSecretary

from .models import RoomScanTag
from .qr import make_room_qr
from .serializers_admin import SchoolCampusSerializer, RoomSerializer, RoomScanTagSerializer
from .utils_rooms import create_room_auto_code


def _png_base64_from_payload(payload: str) -> str:
    img = qrcode.make(payload)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def _to_bool(v, default=False):
    if v is None:
        return default
    if isinstance(v, bool):
        return v
    s = str(v).lower().strip()
    return s in ["1", "true", "yes", "y"]


def _to_float(v, name):
    try:
        return float(v)
    except Exception:
        raise ValueError(f"Invalid {name}")


def _to_int(v, name):
    try:
        return int(v)
    except Exception:
        raise ValueError(f"Invalid {name}")


class AttendanceAdminViewSet(ViewSet):
    """
    ✅ Secrétaire manage:
    - Campus create/list
    - Room create/list (code auto si absent)
    - Tag geo set/update (GPS + radius)
    - Payload QR/NFC + PNG base64 pour impression
    """
    permission_classes = [IsAuthenticated, IsSecretary]

    # =========================================================
    # 🏫 CAMPUS
    # =========================================================
    @action(detail=False, methods=["get"], url_path="campus")
    def campus_list(self, request):
        qs = SchoolCampus.objects.all().order_by("name")
        return ok({"items": SchoolCampusSerializer(qs, many=True).data}, "Campus list ✅")

    @action(detail=False, methods=["post"], url_path="campus/create")
    def campus_create(self, request):
        name = (request.data.get("name") or "").strip()
        if not name:
            return bad("name is required", 400)

        try:
            center_lat = _to_float(request.data.get("center_lat"), "center_lat")
            center_lng = _to_float(request.data.get("center_lng"), "center_lng")
            radius_m = _to_int(request.data.get("radius_m", 150), "radius_m")
        except ValueError as e:
            return bad(str(e), 400)

        if radius_m <= 0 or radius_m > 5000:
            return bad("radius_m must be between 1 and 5000", 400)

        campus = SchoolCampus.objects.create(
            name=name,
            center_lat=center_lat,
            center_lng=center_lng,
            radius_m=radius_m,
            is_active=True,
            address_line1=request.data.get("address_line1"),
            address_line2=request.data.get("address_line2"),
            city=request.data.get("city"),
            province=request.data.get("province"),
            postal_code=request.data.get("postal_code"),
            country=request.data.get("country") or "South Africa",
        )
        return ok({"campus": SchoolCampusSerializer(campus).data}, "Campus created ✅")

    # =========================================================
    # 🧱 ROOMS
    # =========================================================
    @action(detail=False, methods=["get"], url_path="rooms")
    def rooms_list(self, request):
        """
        GET /api/admin/attendance/rooms/?campus_id=1
        """
        campus_id = request.query_params.get("campus_id")
        qs = Room.objects.all().order_by("code")
        if campus_id:
            qs = qs.filter(campus_id=campus_id)
        return ok({"items": RoomSerializer(qs, many=True).data}, "Rooms ✅")

    @action(detail=False, methods=["post"], url_path="room/create")
    def room_create(self, request):
        """
        POST /api/admin/attendance/room/create/
        body:
        {
          "code": "R7",            # optionnel (si absent => auto)
          "campus_id": 1,          # optionnel
          "name": "Room 7 - Main Building",
          "capacity": 30,
          "is_active": true
        }
        """
        code = (request.data.get("code") or "").strip()
        name = (request.data.get("name") or "").strip()
        if not name:
            return bad("name is required", 400)

        campus_id = request.data.get("campus_id")
        campus = None
        if campus_id:
            campus = SchoolCampus.objects.filter(id=campus_id).first()
            if not campus:
                return bad("Campus not found", 404)

        capacity = request.data.get("capacity")
        is_active = _to_bool(request.data.get("is_active"), True)

        # ✅ code fourni => create/update (logique simple)
        if code:
            room, created = Room.objects.get_or_create(
                code=code,
                defaults={
                    "campus": campus,
                    "name": name,
                    "capacity": capacity,
                    "is_active": is_active,
                }
            )
            if not created:
                room.campus = campus
                room.name = name
                room.capacity = capacity
                room.is_active = is_active
                room.save()
            return ok({"room": RoomSerializer(room).data, "created": created}, "Room saved ✅")

        # ✅ code absent => auto génération R{n}
        room = create_room_auto_code(
            campus=campus,
            name=name,
            capacity=capacity,
            is_active=is_active,
        )
        return ok({"room": RoomSerializer(room).data, "created": True}, f"Room created with code {room.code} ✅")

    # =========================================================
    # 📍 TAG GEO: create/update + payload + PNG
    # =========================================================
    @action(detail=False, methods=["post"], url_path="room-tag/set-geo")
    def set_room_tag_geo(self, request):
        """
        POST /api/admin/attendance/room-tag/set-geo/
        body:
        {
          "room_code": "R7",
          "lat": -26.2,
          "lng": 28.0,
          "radius_m": 30,
          "return_png": true,

          # optionnel: si room n'existe pas => créer
          "auto_create_room": true,
          "campus_id": 1,
          "name": "Room 7 - Main Building",
          "capacity": 30
        }
        """
        room_code = (request.data.get("room_code") or "").strip()
        if not room_code:
            return bad("room_code is required", 400)

        auto_create_room = _to_bool(request.data.get("auto_create_room"), False)
        campus_id = request.data.get("campus_id")

        room = Room.objects.select_related("campus").filter(code=room_code).first()

        # ✅ si room absent et auto_create_room=True => créer
        if not room and auto_create_room:
            if not campus_id:
                return bad("campus_id is required to auto_create_room", 400)
            campus = SchoolCampus.objects.filter(id=campus_id).first()
            if not campus:
                return bad("Campus not found", 404)

            name = (request.data.get("name") or "").strip() or room_code
            capacity = request.data.get("capacity")

            room = Room.objects.create(
                code=room_code,
                campus=campus,
                name=name,
                capacity=capacity,
                is_active=True,
            )

        if not room:
            return bad("Room not found", 404)

        lat = request.data.get("lat")
        lng = request.data.get("lng")
        if lat is None or lng is None:
            return bad("lat and lng are required", 400)

        radius_m = request.data.get("radius_m", 30)
        return_png = _to_bool(request.data.get("return_png"), True)

        try:
            lat_f = _to_float(lat, "lat")
            lng_f = _to_float(lng, "lng")
            radius_m = _to_int(radius_m, "radius_m")
        except ValueError as e:
            return bad(str(e), 400)

        if radius_m <= 0 or radius_m > 500:
            return bad("radius_m must be between 1 and 500", 400)

        # ✅ Security: secrétaire doit être dans le campus
        if room.campus and not is_within_campus(room.campus, lat_f, lng_f):
            return bad("You must be inside campus to set room geo", 403)

        with transaction.atomic():
            tag, created = RoomScanTag.objects.get_or_create(room=room)
            tag.latitude = lat_f
            tag.longitude = lng_f
            tag.radius_m = radius_m
            tag.is_active = True
            tag.save()

        payload = make_room_qr(room.code, str(tag.id))

        data = {
            "room": RoomSerializer(room).data,
            "tag": RoomScanTagSerializer(tag).data,
            "payload": payload,  # ✅ à imprimer en QR + écrire en NFC
            "created": created,
        }
        if return_png:
            data["qr_png_base64"] = _png_base64_from_payload(payload)

        return ok(data, "Room tag geo saved ✅")

    @action(detail=False, methods=["get"], url_path="room-tag/print")
    def room_tag_print(self, request):
        """
        GET /api/admin/attendance/room-tag/print/?room_code=R7&png=1
        """
        room_code = (request.query_params.get("room_code") or "").strip()
        if not room_code:
            return bad("room_code is required", 400)

        room = Room.objects.select_related("campus").filter(code=room_code).first()
        if not room:
            return bad("Room not found", 404)

        tag = RoomScanTag.objects.filter(room=room, is_active=True).first()
        if not tag:
            return bad("Room tag not configured", 403)

        payload = make_room_qr(room.code, str(tag.id))
        data = {
            "room": RoomSerializer(room).data,
            "tag": RoomScanTagSerializer(tag).data,
            "payload": payload,
        }

        if _to_bool(request.query_params.get("png"), False):
            data["qr_png_base64"] = _png_base64_from_payload(payload)

        return ok(data, "QR ready ✅")

    @action(detail=False, methods=["post"], url_path="room-tag/toggle")
    def room_tag_toggle(self, request):
        """
        POST /api/admin/attendance/room-tag/toggle/
        body: { "room_code": "R7", "is_active": true }
        """
        room_code = (request.data.get("room_code") or "").strip()
        if not room_code:
            return bad("room_code is required", 400)

        room = Room.objects.filter(code=room_code).first()
        if not room:
            return bad("Room not found", 404)

        tag = RoomScanTag.objects.filter(room=room).first()
        if not tag:
            return bad("Room tag not configured", 404)

        tag.is_active = _to_bool(request.data.get("is_active"), True)
        tag.save(update_fields=["is_active", "updated_at"])

        return ok({"tag": RoomScanTagSerializer(tag).data}, "Updated ✅")