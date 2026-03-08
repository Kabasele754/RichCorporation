from collections import defaultdict

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from apps.abc_apps.attendance.models import ReenrollmentIntent
from apps.abc_apps.academics.services.promotion_service import promote_students_to_next_period


@shared_task
def process_reenrollment_intents():
    today = timezone.localdate()

    intents = list(
        ReenrollmentIntent.objects
        .select_related("student", "from_period", "to_period")
        .filter(
            status="pending",
            execute_after__isnull=False,
            execute_after__lte=today,
        )
        .order_by("created_at")
    )

    processed = 0
    failed = 0

    # ✅ on groupe par (from_period, to_period)
    buckets = defaultdict(list)
    for intent in intents:
        buckets[(intent.from_period_id, intent.to_period_id)].append(intent)

    for (_, _), bucket in buckets.items():
        yes_intents = [x for x in bucket if x.will_return]
        no_intents = [x for x in bucket if not x.will_return]

        # 1) traiter les "non"
        for intent in no_intents:
            try:
                intent.status = "rejected"
                intent.processed_at = timezone.now()
                intent.decided_at = timezone.now()
                intent.save(update_fields=["status", "processed_at", "decided_at", "updated_at"])
                processed += 1
            except Exception as e:
                print(f"[process_reenrollment_intents] reject failed intent_id={intent.id} error={e}")
                failed += 1

        # 2) traiter les "oui"
        if yes_intents:
            try:
                from_period = yes_intents[0].from_period
                to_period = yes_intents[0].to_period
                student_ids = [x.student_id for x in yes_intents]

                result = promote_students_to_next_period(
                    from_period=from_period,
                    to_period=to_period,
                    student_ids=student_ids,
                    created_by=None,
                )

                now_dt = timezone.now()
                for intent in yes_intents:
                    intent.status = "approved"
                    intent.processed_at = now_dt
                    intent.decided_at = now_dt
                    intent.save(update_fields=["status", "processed_at", "decided_at", "updated_at"])

                processed += len(yes_intents)

                print(
                    f"[process_reenrollment_intents] promoted "
                    f"from={from_period.code} to={to_period.code} "
                    f"created={result['created']} skipped={result['skipped']}"
                )

            except Exception as e:
                print(f"[process_reenrollment_intents] promotion failed error={e}")
                for intent in yes_intents:
                    try:
                        intent.status = "rejected"
                        intent.processed_at = timezone.now()
                        intent.decided_at = timezone.now()
                        intent.reason = ((intent.reason or "") + f"\n[System] Promotion failed: {e}").strip()
                        intent.save(update_fields=["status", "processed_at", "decided_at", "reason", "updated_at"])
                    except Exception:
                        pass
                failed += len(yes_intents)

    print(f"[process_reenrollment_intents] done processed={processed} failed={failed}")
    return {"processed": processed, "failed": failed}


