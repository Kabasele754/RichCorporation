# apps/abc_apps/academics/utils.py
from django.utils import timezone
from django.db.models import Q

from apps.abc_apps.academics.models import (
    AcademicPeriod,
    StudentMonthlyEnrollment,
    TeacherCourseAssignment,
)

def get_or_create_period_from_date(d):
    # ✅ AcademicPeriod unique_together = (year, month)
    period, _ = AcademicPeriod.objects.get_or_create(
        year=d.year,
        month=d.month,
        defaults={"is_closed": False},
    )
    return period

def get_active_enrollment_for_student(student):
    today = timezone.localdate()
    period = get_or_create_period_from_date(today)
    enroll = (
        StudentMonthlyEnrollment.objects
        .select_related("group__room", "group__level", "period")
        .filter(student=student, period=period, status="active")
        .first()
    )
    return enroll, period

def get_teacher_active_groups(teacher_profile):
    today = timezone.localdate()
    period = get_or_create_period_from_date(today)

    group_ids = list(
        TeacherCourseAssignment.objects
        .filter(teacher=teacher_profile, period=period)
        .exclude(monthly_group__isnull=True)
        .values_list("monthly_group_id", flat=True)
        .distinct()
    )
    return group_ids, period


