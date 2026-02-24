# apps/abc_apps/academics/utils.py
from django.utils import timezone
from apps.abc_apps.academics.models import AcademicPeriod, StudentMonthlyEnrollment

def get_or_create_period_from_date(d):
    key = f"{d.year:04d}-{d.month:02d}"
    period, _ = AcademicPeriod.objects.get_or_create(
        key=key,
        defaults={"year": d.year, "month": d.month},
    )
    return period

def get_active_enrollment_for_student(student):
    today = timezone.localdate()
    period = get_or_create_period_from_date(today)
    print(f"Looking for active enrollment for student {student.student_code} in period {period.key}")
    enroll = (
        StudentMonthlyEnrollment.objects
        .select_related("group__room", "group__level", "period")
        .filter(student=student, period=period, status="active")
        .first()
    )
    print(f"Found enrollment for student {student.student_code} in period {period.key}: {enroll}")
    return enroll, period