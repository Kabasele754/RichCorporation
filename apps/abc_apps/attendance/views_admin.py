# apps/attendance/views_admin.py (ou attendance/admin_views.py)
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
    # 🏫 CAMPUS (UPDATE GEO)
    # =========================================================
    @action(detail=False, methods=["post"], url_path="campus/set-geo")
    def campus_set_geo(self, request):
        """
        POST /api/admin/attendance/campus/set-geo/
        body:
        {
          "campus_id": 1,          # required
          "center_lat": -26.2,     # required
          "center_lng": 28.0,      # required
          "radius_m": 150,         # optional (default keep current)
          "is_active": true        # optional
        }
        """
        campus_id = request.data.get("campus_id")
        if campus_id in [None, ""]:
            return bad("campus_id is required", 400)

        campus = SchoolCampus.objects.filter(id=campus_id).first()
        if not campus:
            return bad("Campus not found", 404)

        lat = request.data.get("center_lat")
        lng = request.data.get("center_lng")

        if lat is None or lng is None:
            return bad("center_lat and center_lng are required", 400)

        try:
            lat_f = _to_float(lat, "center_lat")
            lng_f = _to_float(lng, "center_lng")
        except ValueError as e:
            return bad(str(e), 400)

        # radius optional
        radius_m = request.data.get("radius_m")
        if radius_m in [None, ""]:
            radius_val = campus.radius_m
        else:
            try:
                radius_val = _to_int(radius_m, "radius_m")
            except ValueError as e:
                return bad(str(e), 400)

        if radius_val <= 0 or radius_val > 5000:
            return bad("radius_m must be between 1 and 5000", 400)

        campus.center_lat = lat_f
        campus.center_lng = lng_f
        campus.radius_m = radius_val

        # optional is_active
        if request.data.get("is_active") is not None:
            campus.is_active = _to_bool(request.data.get("is_active"), campus.is_active)

        campus.save()
        return ok({"campus": SchoolCampusSerializer(campus).data}, "Campus geo updated ✅")

    # =========================================================
    # 🧱 ROOMS
    # =========================================================
    @action(detail=False, methods=["get"], url_path="rooms")
    def rooms_list(self, request):
        campus_id = request.query_params.get("campus_id")
        qs = Room.objects.all().order_by("code")
        if campus_id:
            qs = qs.filter(campus_id=campus_id)
        return ok({"items": RoomSerializer(qs, many=True).data}, "Rooms ✅")

    @action(detail=False, methods=["post"], url_path="room/create")
    def room_create(self, request):
        code = (request.data.get("code") or "").strip()
        name = (request.data.get("name") or "").strip()
        if not name:
            return bad("name is required", 400)

        campus_id = request.data.get("campus_id")
        campus = None
        if campus_id not in [None, ""]:
            campus = SchoolCampus.objects.filter(id=campus_id).first()
            if not campus:
                return bad("Campus not found", 404)

        # capacity
        capacity = request.data.get("capacity")
        if capacity not in [None, ""]:
            try:
                capacity = int(capacity)
            except Exception:
                return bad("Invalid capacity", 400)
        else:
            capacity = None

        is_active = _to_bool(request.data.get("is_active"), True)

        # ✅ building / floor (si ton modèle les a)
        building = (request.data.get("building") or "").strip() or None

        floor = request.data.get("floor", 0)
        try:
            floor = int(floor)
        except Exception:
            return bad("Invalid floor", 400)

        if floor < 0 or floor > 3:   # ✅ 4 floors = 0..3
            return bad("floor out of range (0..3)", 400)

        # ✅ code fourni
        if code:
            room, created = Room.objects.get_or_create(
                code=code,
                defaults={
                    "campus": campus,
                    "name": name,
                    "capacity": capacity,
                    "is_active": is_active,
                    "building": building,
                    "floor": floor,
                },
            )
            if not created:
                room.campus = campus
                room.name = name
                room.capacity = capacity
                room.is_active = is_active
                room.building = building
                room.floor = floor
                room.save()

            return ok({"room": RoomSerializer(room).data, "created": created}, "Room saved ✅")

        # ✅ auto code
        room = create_room_auto_code(
            campus=campus,
            name=name,
            capacity=capacity,
            is_active=is_active,
            building=building,
            floor=floor,
        )
        return ok({"room": RoomSerializer(room).data, "created": True}, f"Room created with code {room.code} ✅")
    
    # =========================================================
    # 🧱 ROOMS (EDIT / DELETE)
    # =========================================================
    @action(detail=False, methods=["post"], url_path="room/update")
    def room_update(self, request):
        """
        POST /api/admin/attendance/room/update/
        body:
        {
        "id": 12,                      # required
        "campus_id": 1,                # optional
        "name": "Room 7 - Main",
        "capacity": 30,
        "is_active": true,
        "building": "Main Building",   # optional
        "floor": 2                     # optional
        }
        """
        room_id = request.data.get("id")
        if room_id in [None, ""]:
            return bad("id is required", 400)

        room = Room.objects.select_related("campus").filter(id=room_id).first()
        if not room:
            return bad("Room not found", 404)

        name = (request.data.get("name") or "").strip()
        if not name:
            return bad("name is required", 400)

        campus_id = request.data.get("campus_id")
        is_active = _to_bool(request.data.get("is_active"), room.is_active)

        building = (request.data.get("building") or "").strip() or None

        floor = request.data.get("floor", room.floor)
        try:
            floor = int(floor)
        except Exception:
            return bad("Invalid floor", 400)

        if floor < -5 or floor > 200:
            return bad("floor out of range", 400)

        capacity = request.data.get("capacity")
        if capacity not in [None, ""]:
            try:
                capacity = int(capacity)
            except Exception:
                return bad("Invalid capacity", 400)
        else:
            capacity = None

        campus = None
        if campus_id not in [None, ""]:
            campus = SchoolCampus.objects.filter(id=campus_id).first()
            if not campus:
                return bad("Campus not found", 404)

        # ✅ code non modifiable
        room.name = name
        room.capacity = capacity
        room.is_active = is_active
        room.campus = campus
        room.building = building
        room.floor = floor
        room.save()

        return ok({"room": RoomSerializer(room).data}, "Room updated ✅")
    @action(detail=False, methods=["post"], url_path="room/delete")
    def room_delete(self, request):
        """
        POST /api/admin/attendance/room/delete/
        body:
        {
          "id": 12,
          "hard": false     # default false => soft delete (is_active=false)
        }
        """
        room_id = request.data.get("id")
        if room_id in [None, ""]:
            return bad("id is required", 400)

        hard = _to_bool(request.data.get("hard"), False)

        room = Room.objects.filter(id=room_id).first()
        if not room:
            return bad("Room not found", 404)

        # ✅ delete tag aussi si hard delete
        if hard:
            with transaction.atomic():
                RoomScanTag.objects.filter(room=room).delete()
                room.delete()
            return ok({"deleted": True, "hard": True}, "Room deleted permanently ✅")

        # soft delete
        room.is_active = False
        room.save(update_fields=["is_active"])
        return ok({"deleted": True, "hard": False}, "Room disabled ✅")


     # =========================================================
    # 📍 TAG GEO: create/update + payload + PNG
    # =========================================================
    @action(detail=False, methods=["post"], url_path="room-tag/set-geo")
    def set_room_tag_geo(self, request):
        room_code = (request.data.get("room_code") or "").strip()
        if not room_code:
            return bad("room_code is required", 400)

        auto_create_room = _to_bool(request.data.get("auto_create_room"), False)
        campus_id = request.data.get("campus_id")

        room = Room.objects.select_related("campus").filter(code=room_code).first()

        # ✅ auto create si absent
        if not room and auto_create_room:
            if not campus_id:
                return bad("campus_id is required to auto_create_room", 400)

            campus = SchoolCampus.objects.filter(id=campus_id).first()
            if not campus:
                return bad("Campus not found", 404)

            name = (request.data.get("name") or "").strip() or room_code

            capacity = request.data.get("capacity")
            if capacity not in [None, ""]:
                try:
                    capacity = int(capacity)
                except Exception:
                    return bad("Invalid capacity", 400)
            else:
                capacity = None

            room = Room.objects.create(
                code=room_code,
                campus=campus,
                name=name,
                capacity=capacity,
                is_active=True,
            )

        if not room:
            return bad("Room not found", 404)

        # --------------------------
        # lat/lng required
        # --------------------------
        lat = request.data.get("lat")
        lng = request.data.get("lng")
        if lat is None or lng is None:
            return bad("lat and lng are required", 400)

        radius_m = request.data.get("radius_m", 30)
        return_png = _to_bool(request.data.get("return_png"), True)

        # ✅ NEW: accuracy tolerance (GPS)
        accuracy_m = request.data.get("accuracy_m", 0)

        try:
            lat_f = _to_float(lat, "lat")
            lng_f = _to_float(lng, "lng")
            radius_m = _to_int(radius_m, "radius_m")
            accuracy_m = _to_int(accuracy_m, "accuracy_m")
        except ValueError as e:
            return bad(str(e), 400)

        if radius_m <= 0 or radius_m > 500:
            return bad("radius_m must be between 1 and 500", 400)

        # ✅ clamp tolerance (indoor GPS can be crazy)
        #   - keep max 200m extra to avoid abuse
        tol = max(0, min(int(accuracy_m or 0), 200))

        # --------------------------
        # ✅ Security: must be inside campus (with tolerance)
        # --------------------------
        if room.campus:
            ok_in, dist_m, allowed_m = is_within_campus(
                room.campus,
                lat_f,
                lng_f,
                extra_m=tol,
            )

            if not ok_in:
                # message clair (pratique pour debug)
                return bad(
                    f"You must be inside campus to set room geo "
                    f"(dist={dist_m:.1f}m / allowed={allowed_m:.1f}m, GPS±{tol}m)",
                    403,
                )

        # --------------------------
        # Save/update tag
        # --------------------------
        with transaction.atomic():
            tag, created = RoomScanTag.objects.get_or_create(room=room)
            tag.latitude = lat_f
            tag.longitude = lng_f
            tag.radius_m = radius_m
            tag.is_active = True
            tag.save()

        # ✅ payload v2 signé ABCR|ROOM|room|tag|sig
        payload = make_room_qr(room.code, str(tag.id))

        data = {
            "room": RoomSerializer(room).data,
            "tag": RoomScanTagSerializer(tag).data,
            "payload": payload,
            "created": created,
        }

        if return_png:
            data["qr_png_base64"] = _png_base64_from_payload(payload)

        # ✅ Bonus debug (optionnel)
        data["security"] = {
            "gps_accuracy_m": tol,
            "campus_checked": bool(room.campus_id),
        }

        return ok(data, "Room tag geo saved ✅")
    
    
    @action(detail=False, methods=["get"], url_path="room-tag/print")
    def room_tag_print(self, request):
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