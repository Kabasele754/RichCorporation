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
                # ✅ student chose not to return
                if not intent.will_return:
                    intent.status = "rejected"
                    intent.processed_at = timezone.now()
                    intent.decided_at = timezone.now()
                    intent.save(
                        update_fields=[
                            "status",
                            "processed_at",
                            "decided_at",
                            "updated_at",
                        ]
                    )
                    processed += 1
                    continue

                # ✅ recover current group from current period enrollment
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
                    intent.status = "rejected"
                    intent.processed_at = timezone.now()
                    intent.decided_at = timezone.now()
                    intent.reason = (
                        (intent.reason or "") +
                        "\n[System] Failed to process re-enrollment: source group not found."
                    ).strip()
                    intent.save(
                        update_fields=[
                            "status",
                            "processed_at",
                            "decided_at",
                            "reason",
                            "updated_at",
                        ]
                    )
                    failed += 1
                    continue

                target_group = current.group

                # ✅ create next enrollment only now
                next_enroll, created = StudentMonthlyEnrollment.objects.get_or_create(
                    student=intent.student,
                    period=intent.to_period,
                    defaults={
                        "group": target_group,
                        "status": "pending",  # ou active selon ta logique
                    },
                )

                # ✅ optional harmonization
                if not created:
                    changed = False

                    if getattr(next_enroll, "group_id", None) is None and target_group:
                        next_enroll.group = target_group
                        changed = True

                    if getattr(next_enroll, "status", None) in [None, "", "cancelled"]:
                        next_enroll.status = "pending"
                        changed = True

                    if changed:
                        next_enroll.save()

                # ✅ mark intent approved
                intent.status = "approved"
                intent.processed_at = timezone.now()
                intent.decided_at = timezone.now()
                intent.save(
                    update_fields=[
                        "status",
                        "processed_at",
                        "decided_at",
                        "updated_at",
                    ]
                )
                processed += 1

        except Exception as e:
            print(f"[process_reenrollment_intents] failed intent_id={intent.id} error={e}")
            try:
                intent.status = "rejected"
                intent.processed_at = timezone.now()
                intent.decided_at = timezone.now()
                intent.reason = (
                    (intent.reason or "") +
                    f"\n[System] Processing error: {e}"
                ).strip()
                intent.save(
                    update_fields=[
                        "status",
                        "processed_at",
                        "decided_at",
                        "reason",
                        "updated_at",
                    ]
                )
            except Exception as inner_e:
                print(f"[process_reenrollment_intents] secondary save failed intent_id={intent.id} error={inner_e}")
            failed += 1

    print(f"[process_reenrollment_intents] done processed={processed} failed={failed}")
    return {
        "processed": processed,
        "failed": failed,
    }