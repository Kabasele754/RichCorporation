# =========================================
# apps/dashboards/services/principal.py
# =========================================
from datetime import timedelta
from django.core.exceptions import FieldError
from django.utils import timezone
from django.db.models import Count

from apps.abc_apps.dashboards.services.utils import (
    last_n_days_dates, weekday_labels, today_date, now_dt
)

from apps.abc_apps.attendance.models import DailyRoomCheckIn, TeacherCheckIn
from apps.abc_apps.gate_security.models import GateEntry
from apps.abc_apps.library.models import Loan
from apps.abc_apps.speeches.models import Speech

from apps.abc_apps.academics.models import MonthlyClassGroup, Room


def _filter_by_day(qs, day):
    """
    Certains modèles ont `date`, d'autres `scanned_at`.
    On tente proprement sans casser.
    """
    try:
        return qs.filter(date=day)
    except FieldError:
        pass

    try:
        return qs.filter(scanned_at__date=day)
    except FieldError:
        pass

    # dernier fallback: created_at si jamais
    try:
        return qs.filter(created_at__date=day)
    except FieldError:
        return qs.none()


def _group_label(g: MonthlyClassGroup) -> str:
    try:
        return g.label
    except Exception:
        level = getattr(getattr(g, "level", None), "label", "") or ""
        room_code = getattr(getattr(g, "room", None), "code", "") or ""
        gn = getattr(g, "group_name", "") or ""
        return f"{level} {gn} • {room_code}".strip()


def _room_label(r: Room) -> str:
    code = getattr(r, "code", "") or ""
    name = getattr(r, "name", "") or ""
    return f"{code} • {name}".strip(" •")


def build_principal_overview(user, days: int = 7):
    """
    KPI + charts (N days) + alerts
    ✅ FIX: pas de session__date (DailyRoomCheckIn n'a pas session)
    ✅ FIX: by_class_today basé sur monthly_group/room
    """
    today = today_date()
    now = now_dt()

    # ---------------- KPIs ----------------
    students_present_today = (
        _filter_by_day(DailyRoomCheckIn.objects.all(), today)
        .values("student_id")
        .distinct()
        .count()
    )

    teachers_checked_today = (
        _filter_by_day(TeacherCheckIn.objects.all(), today)
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

    speeches_this_month = Speech.objects.filter(
        created_at__year=today.year,
        created_at__month=today.month,
    ).count()

    # ---------------- Chart: attendance last N days ----------------
    dates = last_n_days_dates(days)
    labels = weekday_labels(dates)

    present_series = []
    for d in dates:
        c = (
            _filter_by_day(DailyRoomCheckIn.objects.all(), d)
            .values("student_id")
            .distinct()
            .count()
        )
        present_series.append(c)

    # ---------------- By class today (sans ClassSession) ----------------
    # On essaye d'abord monthly_group si dispo, sinon room.
    checks_today = _filter_by_day(DailyRoomCheckIn.objects.all(), today)

    by_class_today = []

    # A) group-based
    try:
        agg = (
            checks_today
            .values("monthly_group_id")
            .annotate(present=Count("student_id", distinct=True))
            .order_by("-present")
        )
        group_ids = [x["monthly_group_id"] for x in agg if x["monthly_group_id"]]
        groups_map = {
            g.id: g for g in MonthlyClassGroup.objects.select_related("level", "room", "period").filter(id__in=group_ids)
        }

        for x in agg:
            gid = x["monthly_group_id"]
            if not gid:
                continue
            g = groups_map.get(gid)
            by_class_today.append({
                "class": _group_label(g) if g else f"Group #{gid}",
                "present": x["present"],
                "monthly_group_id": gid,
            })

    except FieldError:
        # B) fallback room-based
        agg = (
            checks_today
            .values("room_id")
            .annotate(present=Count("student_id", distinct=True))
            .order_by("-present")
        )
        room_ids = [x["room_id"] for x in agg if x["room_id"]]
        rooms_map = {r.id: r for r in Room.objects.filter(id__in=room_ids)}

        for x in agg:
            rid = x["room_id"]
            if not rid:
                continue
            r = rooms_map.get(rid)
            by_class_today.append({
                "class": _room_label(r) if r else f"Room #{rid}",
                "present": x["present"],
                "room_id": rid,
            })

    # ---------------- Alerts ----------------
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
