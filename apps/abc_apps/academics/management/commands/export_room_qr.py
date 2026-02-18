from django.core.management.base import BaseCommand
import os
import qrcode

from apps.abc_apps.academics.models import Room
from apps.abc_apps.attendance.qr import make_room_qr

class Command(BaseCommand):
    help = "Export static signed QR for each room"

    def add_arguments(self, parser):
        parser.add_argument("--out", default="room_qr", help="Output folder")

    def handle(self, *args, **opts):
        out = opts["out"]
        os.makedirs(out, exist_ok=True)

        rooms = Room.objects.all().order_by("code")
        for r in rooms:
            data = make_room_qr(r.code)  # ✅ ABCR|R1|sig
            img = qrcode.make(data)
            path = os.path.join(out, f"{r.code}.png")
            img.save(path)
            self.stdout.write(f"{r.code} => {data}  [{path}]")

        self.stdout.write(self.style.SUCCESS("Done ✅"))
