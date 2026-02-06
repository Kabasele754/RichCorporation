# =========================================
# apps/library/services/reminders.py
# =========================================
from datetime import timedelta
from django.utils import timezone
from apps.abc_apps.library.models import Loan
from apps.abc_apps.library.models_notifications import Notification

RETURN_REMINDER_BEFORE_MIN = 30

def send_reading_reminders():
    """
    Smart reminder:
    - for active book loans, send max 1 reminder per 24h
    """
    now = timezone.now()
    last_24h = now - timedelta(hours=24)

    qs = Loan.objects.select_related("item", "borrowed_by").filter(
        returned_at__isnull=True,
        item__item_type="book",
    )

    for loan in qs:
        if loan.last_read_reminder_at and loan.last_read_reminder_at >= last_24h:
            continue

        Notification.objects.create(
            user=loan.borrowed_by,
            title="Reading time 📚",
            message=f"Reminder: read your book '{loan.item.title}' today to improve your English.",
            data={"loan_id": loan.id, "item_code": loan.item.code, "type": "reading"},
        )
        loan.last_read_reminder_at = now
        loan.save(update_fields=["last_read_reminder_at"])


def send_return_reminders():
    """
    - 30 minutes before due_at: reminder (avoid spam)
    - overdue: reminder max every 6 hours
    """
    now = timezone.now()
    six_hours_ago = now - timedelta(hours=6)

    qs = Loan.objects.select_related("item", "borrowed_by").filter(
        returned_at__isnull=True,
        due_at__isnull=False,
    )

    for loan in qs:
        # due soon
        if loan.due_at and now <= loan.due_at <= now + timedelta(minutes=RETURN_REMINDER_BEFORE_MIN):
            if loan.last_return_reminder_at and loan.last_return_reminder_at >= now - timedelta(hours=2):
                continue

            Notification.objects.create(
                user=loan.borrowed_by,
                title="Return reminder ⏰",
                message=f"Please return '{loan.item.title}' soon (due in ~{RETURN_REMINDER_BEFORE_MIN} minutes).",
                data={"loan_id": loan.id, "item_code": loan.item.code, "type": "return_due_soon"},
            )
            loan.last_return_reminder_at = now
            loan.save(update_fields=["last_return_reminder_at"])
            continue

        # overdue
        if loan.due_at and now > loan.due_at:
            if loan.last_return_reminder_at and loan.last_return_reminder_at >= six_hours_ago:
                continue

            Notification.objects.create(
                user=loan.borrowed_by,
                title="Overdue ⚠️",
                message=f"'{loan.item.title}' is overdue. Please return it as soon as possible.",
                data={"loan_id": loan.id, "item_code": loan.item.code, "type": "overdue"},
            )
            loan.last_return_reminder_at = now
            loan.save(update_fields=["last_return_reminder_at"])
