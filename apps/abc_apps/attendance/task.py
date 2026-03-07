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
        .select_related("student", "from_period", "to_period")
        .filter(status="pending", execute_after__lte=today)
        .order_by("created_at")
    )

    for intent in intents:
        try:
            with transaction.atomic():
                if not intent.will_return:
                    intent.status = "processed"
                    intent.processed_at = timezone.now()
                    intent.save(update_fields=["status", "processed_at"])
                    continue

                # 🔎 retrouver l’enrollment source
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
                    intent.save(update_fields=["status"])
                    continue

                # ✅ créer prochain enrollment seulement MAINTENANT
                next_enroll, created = StudentMonthlyEnrollment.objects.get_or_create(
                    student=intent.student,
                    period=intent.to_period,
                    defaults={
                        "group": current.group,
                        "status": "pending",   # ou active selon ta logique
                    },
                )

                if not created:
                    # optionnel: ne pas écraser si déjà configuré par admin
                    pass

                intent.status = "processed"
                intent.processed_at = timezone.now()
                intent.save(update_fields=["status", "processed_at"])

        except Exception:
            intent.status = "failed"
            intent.save(update_fields=["status"])