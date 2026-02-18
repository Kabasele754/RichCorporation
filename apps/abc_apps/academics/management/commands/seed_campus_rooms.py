from django.core.management.base import BaseCommand
from django.db import transaction

from apps.abc_apps.academics.models import Room, SchoolCampus


class Command(BaseCommand):
    help = "Seed default campus + rooms (safe, idempotent)."

    DEFAULT_CAMPUS = {
        "name": "ABC International",
        "address_line1": "Braamfontein. Johannesburg, 2017. South Africa",
        "city": "Johannesburg",
        "province": "Gauteng",
        "postal_code": "",
        "country": "South Africa",
        "center_lat": -26.204103,   # ⚠️ change
        "center_lng": 28.047305,    # ⚠️ change
        "radius_m": 150,
        "is_active": True,
    }

    ROOMS = [
        ("R1", "Room 1 - Main Building", 25),
        ("R2", "Room 2 - Main Building", 25),
        ("R3", "Room 3 - Main Building", 30),
        ("R4", "Room 4 - Main Building", 30),
        ("R5", "Room 5 - Main Building", 20),
        ("R6", "Room 6 - Annex", 20),
        ("R7", "Room 7 - Annex", 15),
        ("R8", "Room 8 - Annex", 15),
        ("R9", "Room 9 - Annex", 10),
        ("LAB-A", "Lab A - Computer Room", 18),
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force update existing rooms name/capacity/campus with seed values.",
        )
        parser.add_argument(
            "--attach-existing",
            action="store_true",
            help="Attach default campus to rooms that have no campus (only if nullable campus existed at some point).",
        )

    @transaction.atomic
    def handle(self, *args, **opts):
        force = bool(opts["force"])
        attach_existing = bool(opts["attach_existing"])

        self.stdout.write(self.style.NOTICE("Seeding Default Campus..."))

        campus, campus_created = SchoolCampus.objects.get_or_create(
            name=self.DEFAULT_CAMPUS["name"],
            defaults=self.DEFAULT_CAMPUS,
        )

        # ✅ Update campus fields if changed (safe)
        updated = []
        for k, v in self.DEFAULT_CAMPUS.items():
            if k == "name":
                continue
            if getattr(campus, k) != v and force:
                setattr(campus, k, v)
                updated.append(k)

        if updated:
            campus.save(update_fields=updated)

        self.stdout.write(
            f" - {campus} [{ 'CREATED' if campus_created else ('UPDATED' if updated else 'OK') }]"
        )

        # (optional) attach campus to existing rooms that have campus NULL (only relevant if you allowed null earlier)
        if attach_existing:
            qs = Room.objects.filter(campus__isnull=True)
            count = qs.update(campus=campus)
            self.stdout.write(self.style.WARNING(f"Attached campus to {count} existing rooms (campus was NULL)."))

        self.stdout.write(self.style.NOTICE("Seeding Rooms..."))

        for code, name, capacity in self.ROOMS:
            obj, created = Room.objects.get_or_create(
                code=code,
                defaults={
                    "campus": campus,
                    "name": name,
                    "capacity": capacity,
                    "is_active": True,
                },
            )

            updated_fields = []

            # ✅ if room existed, do NOT override secretary edits unless --force
            if force:
                if obj.campus_id != campus.id:
                    obj.campus = campus
                    updated_fields.append("campus")
                if obj.name != name:
                    obj.name = name
                    updated_fields.append("name")
                if obj.capacity != capacity:
                    obj.capacity = capacity
                    updated_fields.append("capacity")

            # ✅ Always ensure active = True (safe choice)
            if obj.is_active is False:
                obj.is_active = True
                updated_fields.append("is_active")

            if updated_fields:
                obj.save(update_fields=updated_fields)

            status = "CREATED" if created else ("UPDATED" if updated_fields else "OK")
            self.stdout.write(f" - {obj} (cap={obj.capacity}) [{status}]")

        self.stdout.write(self.style.SUCCESS("Campus + Rooms ready ✅"))
