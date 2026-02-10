from django.core.management.base import BaseCommand
from apps.abc_apps.academics.models import AcademicLevel


class Command(BaseCommand):
    help = "Seed default AcademicLevel (code, label, order)"

    LEVELS = [
        # (code, label)
        ("FOUNDATION_1", "Foundation 1"),
        ("FOUNDATION_2", "Foundation 2"),
        ("FOUNDATION_3", "Foundation 3"),
        ("BASIC_1", "Basic 1"),
        ("BASIC_2", "Basic 2"),
        ("INTERMEDIATE_1", "Intermediate 1"),
        ("INTERMEDIATE_2", "Intermediate 2"),
        ("ADVANCED_1", "Advanced 1"),
        ("ADVANCED_2", "Advanced 2"),
    ]

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Seeding AcademicLevel..."))

        for idx, (code, label) in enumerate(self.LEVELS, start=1):
            obj, created = AcademicLevel.objects.get_or_create(
                code=code,
                defaults={"label": label, "order": idx},
            )

            # ✅ Update if changed (safe to re-run)
            updated_fields = []
            if obj.label != label:
                obj.label = label
                updated_fields.append("label")
            if obj.order != idx:
                obj.order = idx
                updated_fields.append("order")

            if updated_fields:
                obj.save(update_fields=updated_fields)

            status = "CREATED" if created else ("UPDATED" if updated_fields else "OK")
            self.stdout.write(f" - {code} → {label} (order={idx}) [{status}]")

        self.stdout.write(self.style.SUCCESS("AcademicLevel ready ✅"))
