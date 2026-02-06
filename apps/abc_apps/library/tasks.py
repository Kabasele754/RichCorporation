from celery import shared_task
from apps.abc_apps.library.services.reminders import send_reading_reminders, send_return_reminders

@shared_task(name="apps.library.tasks.send_reading_reminders_task")
def send_reading_reminders_task():
    """
    Daily reading reminders for active BOOK loans.
    """
    send_reading_reminders()
    return {"status": "ok", "task": "reading_reminders"}

@shared_task(name="apps.library.tasks.send_return_reminders_task")
def send_return_reminders_task():
    """
    Return reminders (due soon + overdue).
    """
    send_return_reminders()
    return {"status": "ok", "task": "return_reminders"}
