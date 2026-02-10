from django.core.management.base import BaseCommand
from apps.abc_apps.academics.models import Room


class Command(BaseCommand):
    help = "Seed default rooms (code, name, capacity, is_active)"

    ROOMS = [
        # code, name, capacity
        ("R1", "Room 1 - Main Building", 25),
        ("R2", "Room 2 - Main Building", 25),
        ("R3", "Room 3 - Main Building", 30),
        ("R4", "Room 4 - Main Building", 30),
        ("R5", "Room 5 - Main Building", 20),
        ("R6", "Room 6 - Annex", 20),
        ("R7", "Room 7 - Annex", 15),
        ("R8", "Room 8 - Annex", 15),
        ("R9", "Room 9 - Annex", 10),
        # Exemple si tu as un labo:
        ("LAB-A", "Lab A - Computer Room", 18),
    ]

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Seeding Rooms..."))

        for code, name, capacity in self.ROOMS:
            obj, created = Room.objects.get_or_create(
                code=code,
                defaults={
                    "name": name,
                    "capacity": capacity,
                    "is_active": True,
                },
            )

            # ✅ Update if changed (safe to re-run)
            updated_fields = []
            if obj.name != name:
                obj.name = name
                updated_fields.append("name")
            if obj.capacity != capacity:
                obj.capacity = capacity
                updated_fields.append("capacity")
            if obj.is_active is False:
                obj.is_active = True
                updated_fields.append("is_active")

            if updated_fields:
                obj.save(update_fields=updated_fields)

            status = "CREATED" if created else ("UPDATED" if updated_fields else "OK")
            self.stdout.write(f" - {obj} (cap={capacity}) [{status}]")

        self.stdout.write(self.style.SUCCESS("Rooms ready ✅"))
