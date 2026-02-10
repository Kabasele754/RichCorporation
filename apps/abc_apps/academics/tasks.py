# apps/abc_apps/academics/tasks.py
from celery import shared_task
from django.utils import timezone
from apps.abc_apps.academics.models import AcademicPeriod

@shared_task
def ensure_periods_for_current_year() -> int:
    year = timezone.localdate().year
    created = 0
    for m in range(1, 13):
        _, was_created = AcademicPeriod.objects.get_or_create(year=year, month=m)
        if was_created:
            created += 1
    return created

@shared_task
def ensure_periods_for_next_year() -> int:
    year = timezone.localdate().year + 1
    created = 0
    for m in range(1, 13):
        _, was_created = AcademicPeriod.objects.get_or_create(year=year, month=m)
        if was_created:
            created += 1
    return created
