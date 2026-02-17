# =========================================
# apps/dashboards/services/principal.py
# =========================================
from datetime import timedelta
from django.utils import timezone
from apps.abc_apps.dashboards.services.utils import last_n_days_dates, weekday_labels, today_date, now_dt

# Core modules
from apps.abc_apps.sessions_abc.models import ClassSession
from apps.abc_apps.attendance.models import DailyRoomCheckIn, TeacherCheckIn
from apps.abc_apps.gate_security.models import GateEntry
from apps.abc_apps.library.models import Loan
from apps.abc_apps.speeches.models import Speech

def build_principal_overview(user, days: int = 7):
    """
    KPI + charts (7 days) + alerts
    """
    today = today_date()
    now = now_dt()

    # --- KPIs ---
    students_present_today = (
        DailyRoomCheckIn.objects
        .filter(session__date=today)
        .values("student_id")
        .distinct()
        .count()
    )

    teachers_checked_today = (
        TeacherCheckIn.objects
        .filter(session__date=today)
        .values("teacher_id")
        .distinct()
        .count()
    )

    visitors_inside = GateEntry.objects.filter(check_out_at__isnull=True).count()
    overstayed_count = GateEntry.objects.filter(
        check_out_at__isnull=True,
        check_in_at__lte=now - timedelta(minutes=30),
    ).count()

    overdue_items = Loan.objects.filter(
        returned_at__isnull=True,
        due_at__isnull=False,
        due_at__lt=now,
    ).count()

    speeches_this_month = Speech.objects.filter(created_at__date__month=today.month, created_at__date__year=today.year).count()

    # --- Chart: attendance last N days ---
    dates = last_n_days_dates(days)
    labels = weekday_labels(dates)
    present_series = []
    for d in dates:
        c = (
            DailyRoomCheckIn.objects
            .filter(session__date=d)
            .values("student_id")
            .distinct()
            .count()
        )
        present_series.append(c)

    # --- By class today (per session) ---
    by_class_today = []
    sessions_today = ClassSession.objects.select_related("classroom").filter(date=today).order_by("classroom__level", "classroom__group_name")
    for s in sessions_today:
        present = (
            DailyRoomCheckIn.objects
            .filter(session=s)
            .values("student_id")
            .distinct()
            .count()
        )
        by_class_today.append({
            "class": f"{s.classroom.level}-{s.classroom.group_name}",
            "session_type": s.session_type,
            "present": present,
            "session_id": s.id,
        })

    # --- Alerts ---
    alerts = []
    if overstayed_count > 0:
        alerts.append({
            "type": "overstay",
            "title": "Visitor overstayed",
            "message": f"{overstayed_count} visitor(s) inside > 30 min",
        })
    if overdue_items > 0:
        alerts.append({
            "type": "overdue",
            "title": "Overdue items",
            "message": f"{overdue_items} book/material overdue",
        })

    return {
        "kpis": [
            {"label": "Students present today", "value": students_present_today, "trend": ""},
            {"label": "Teachers checked-in", "value": teachers_checked_today, "trend": ""},
            {"label": "Visitors inside", "value": visitors_inside, "trend": f"{overstayed_count} overstayed"},
            {"label": "Overdue items", "value": overdue_items, "trend": "⚠️" if overdue_items else "OK"},
            {"label": "Speeches this month", "value": speeches_this_month, "trend": ""},
        ],
        "charts": {
            "attendance_last_days": {
                "labels": labels,
                "series": [{"name": "Present", "data": present_series}],
            },
            "by_class_today": by_class_today,
        },
        "alerts": alerts,
    }
