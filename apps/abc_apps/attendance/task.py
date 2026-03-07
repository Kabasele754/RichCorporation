# apps/abc_apps/attendance/tasks.py

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from apps.abc_apps.attendance.models import ReenrollmentIntent
from apps.abc_apps.academics.models import StudentMonthlyEnrollment


@shared_task
def process_reenrollment_intents():
    today = timezone.localdate()

    intents = (
        ReenrollmentIntent.objects
        .select_related(
            "student",
            "from_period",
            "to_period",
            "target_group",
        )
        .filter(
            status="pending",
            execute_after__isnull=False,
            execute_after__lte=today,
        )
        .order_by("created_at")
    )

    processed = 0
    failed = 0

    for intent in intents:
        try:
            with transaction.atomic():
                # ✅ cas: student ne revient pas
                if not intent.will_return:
                    intent.status = "processed"
                    intent.processed_at = timezone.now()
                    intent.save(update_fields=["status", "processed_at", "updated_at"])
                    processed += 1
                    continue

                target_group = intent.target_group

                # fallback si target_group absent
                if not target_group:
                    current = (
                        StudentMonthlyEnrollment.objects
                        .select_related("group")
                        .filter(
                            student=intent.student,
                            period=intent.from_period,
                        )
                        .first()
                    )
                    if not current or not current.group_id:
                        intent.status = "failed"
                        intent.save(update_fields=["status", "updated_at"])
                        failed += 1
                        continue
                    target_group = current.group

                # ✅ créer enrollment du mois prochain seulement maintenant
                next_enroll, created = StudentMonthlyEnrollment.objects.get_or_create(
                    student=intent.student,
                    period=intent.to_period,
                    defaults={
                        "group": target_group,
                        "status": "pending",  # ou "active" selon ta logique
                    },
                )

                # optionnel: si déjà existe mais vide/inactif, on peut harmoniser
                if not created:
                    if getattr(next_enroll, "group_id", None) is None and target_group:
                        next_enroll.group = target_group
                        next_enroll.save(update_fields=["group"])

                intent.status = "processed"
                intent.processed_at = timezone.now()
                intent.save(update_fields=["status", "processed_at", "updated_at"])
                processed += 1

        except Exception as e:
            print(f"[process_reenrollment_intents] failed intent_id={intent.id} error={e}")
            intent.status = "failed"
            intent.save(update_fields=["status", "updated_at"])
            failed += 1

    print(f"[process_reenrollment_intents] done processed={processed} failed={failed}")
    return {
        "processed": processed,
        "failed": failed,
    }