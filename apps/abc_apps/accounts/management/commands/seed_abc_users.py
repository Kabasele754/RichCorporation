from typing import Optional, Dict, Any, List
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

from apps.abc_apps.accounts.services.onboarding import create_user_with_profile

User = get_user_model()
DEFAULT_PASSWORD = "12345"


def make_email(first_name: str, last_name: str) -> str:
    fn = (first_name or "").strip().lower().replace(" ", ".")
    ln = (last_name or "").strip().lower().replace(" ", ".")
    if not fn and not ln:
        return "user@abc.com"
    if not ln:
        return f"{fn}@abc.com"
    if not fn:
        return f"{ln}@abc.com"
    return f"{fn}.{ln}@abc.com"


class Command(BaseCommand):
    help = "Seed ABC users (principal, secretary, teachers, security, students)"

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Seeding ABC users..."))

        # PRINCIPAL
        self._create_user(
            username="principal.kim",
            role="principal",
            code="PR-001",
            first_name="Kim",
            last_name="Principal",
        )

        # SECRETARY
        self._create_user(
            username="secretary.mary",
            role="secretary",
            code="SE-001",
            first_name="Mary",
            last_name="Secretary",
        )

        # TEACHERS
        teachers = [
            ("teacher.grammar", "grammar", "TC-GR-001", "Grammar", "Teacher"),
            ("teacher.vocabulary", "vocabulary", "TC-VO-001", "Vocabulary", "Teacher"),
            ("teacher.support", "support", "TC-SP-001", "Support", "Teacher"),
        ]
        for username, speciality, code, fn, ln in teachers:
            self._create_user(
                username=username,
                role="teacher",
                code=code,
                first_name=fn,
                last_name=ln,
                extra={"speciality": speciality},
            )

        # SECURITY (multi-shifts)
        securities = [
            ("security.fulltime", ["full_time"], "SG-FT-001", "Fulltime", "Guard"),
            ("security.morning", ["morning", "night"], "SG-001", "Morning", "Guard"),
            ("security.afternoon", ["afternoon", "night"], "SG-002", "Afternoon", "Guard"),
        ]
        for username, shifts, code, fn, ln in securities:
            self._create_user(
                username=username,
                role="security",
                code=code,
                first_name=fn,
                last_name=ln,
                extra={"shifts": shifts},
            )

        # STUDENTS
        levels = [
            ("Foundation 1", "Mandela"),
            ("Foundation 2", "Mandela"),
            ("Foundation 3", "Mandela"),
            ("INT 1", "Washington"),
            ("INT 2", "Washington"),
        ]

        index = 1
        for level, group in levels:
            for _ in range(1, 5):  # 4 students per level
                username = f"student{index:02d}"
                code = f"ST-{index:03d}"

                self._create_user(
                    username=username,
                    role="student",
                    code=code,
                    first_name=f"Student{index:02d}",
                    last_name="ABC",
                    extra={
                        "current_level": level,
                        "group_name": group,
                        "status": "active",
                    },
                )
                index += 1

        self.stdout.write(self.style.SUCCESS("✅ ABC users seeded successfully"))
        self.stdout.write(self.style.SUCCESS("🔑 Default password for all users: 12345"))

    def _create_user(
        self,
        *,
        username: str,
        role: str,
        code: str,
        first_name: str = "",
        last_name: str = "",
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        if User.objects.filter(username=username).exists():
            self.stdout.write(f"⚠️  User '{username}' already exists — skipped")
            return

        email = make_email(first_name, last_name)

        create_user_with_profile(
            username=username,
            password=DEFAULT_PASSWORD,
            role=role,
            email=email,
            first_name=first_name,
            last_name=last_name,
            code=code,
            extra=extra or {},
        )

        self.stdout.write(self.style.SUCCESS(f"✔ Created {role}: {username} ({email})"))
