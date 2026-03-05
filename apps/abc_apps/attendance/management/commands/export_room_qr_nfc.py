# apps/attendance/management/commands/export_room_qr.py
import os
import qrcode
from django.core.management.base import BaseCommand

from apps.abc_apps.academics.models import Room
from apps.abc_apps.attendance.models import RoomScanTag
from apps.abc_apps.attendance.qr import make_room_qr


class Command(BaseCommand):
    help = "Export signed QR (v2) for each room (printable PNG)"

    def add_arguments(self, parser):
        parser.add_argument("--out", default="room_qr", help="Output folder")
        parser.add_argument("--only-active", action="store_true", help="Export only active tags")
        parser.add_argument("--skip-missing-geo", action="store_true", help="Skip rooms without tag lat/lng")

    def handle(self, *args, **opts):
        out = opts["out"]
        only_active = opts["only_active"]
        skip_missing_geo = opts["skip_missing_geo"]

        os.makedirs(out, exist_ok=True)

        exported = 0
        skipped = 0

        for room in Room.objects.all().order_by("code"):
            tag, _ = RoomScanTag.objects.get_or_create(room=room)

            if only_active and not tag.is_active:
                skipped += 1
                continue

            if skip_missing_geo and (tag.latitude is None or tag.longitude is None):
                skipped += 1
                continue

            payload = make_room_qr(room.code, str(tag.id))
            img = qrcode.make(payload)

            path = os.path.join(out, f"{room.code}.png")
            img.save(path)

            exported += 1
            self.stdout.write(f"{room.code} => [{path}]")

        self.stdout.write(self.style.SUCCESS(f"Done ✅ exported={exported} skipped={skipped}"))