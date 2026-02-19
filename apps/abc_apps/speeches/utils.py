from django.utils import timezone
from apps.abc_apps.academics.models import StudentMonthlyEnrollment, get_or_create_period_from_date

def get_active_enrollment_for_student(student_profile):
    today = timezone.localdate()
    period = get_or_create_period_from_date(today)

    enroll = (
        StudentMonthlyEnrollment.objects
        .select_related("group__room", "period")
        .filter(student=student_profile, period=period, status="active")
        .first()
    )
    return enroll, period
