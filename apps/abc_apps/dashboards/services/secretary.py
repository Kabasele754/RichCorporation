# =========================================
# apps/dashboards/services/secretary.py
# =========================================
from django.utils import timezone

from apps.abc_apps.dashboards.services.utils import now_dt
from apps.abc_apps.academics.models import TeacherCourseAssignment
from apps.abc_apps.library.models import Loan
from apps.abc_apps.gate_security.models import GateEntry

from apps.abc_apps.academics.models import MonthlyClassGroup, AcademicPeriod


def _group_label(g: MonthlyClassGroup) -> str:
    # ex: "Foundation 1 A • R2"
    try:
        return g.label
    except Exception:
        level = getattr(getattr(g, "level", None), "label", "") or ""
        room_code = getattr(getattr(g, "room", None), "code", "") or ""
        gn = getattr(g, "group_name", "") or ""
        return f"{level} {gn} • {room_code}".strip()


def _assignment_class_label(a: TeacherCourseAssignment) -> str:
    """
    Priorité:
    1) monthly_group.label (level + group + room)
    2) room code/name (classroom = Room)
    """
    mg = getattr(a, "monthly_group", None)
    if mg:
        return _group_label(mg)

    room = getattr(a, "classroom", None)  # classroom = Room
    if room:
        code = getattr(room, "code", "") or ""
        name = getattr(room, "name", "") or ""
        return f"{code} • {name}".strip(" •")
    return "—"


def _get_current_period(now):
    """
    Essaie de trouver la période courante.
    - si AcademicPeriod a year/month -> filtre dessus
    - sinon essaye key (ex: "February 2026")
    - sinon fallback: dernière période
    """
    qs = AcademicPeriod.objects.all()

    # 1) year/month
    try:
        # si ces champs existent, Django va accepter le filter
        p = qs.filter(year=now.year, month=now.month).order_by("-year", "-month").first()
        if p:
            return p
    except Exception:
        pass

    # 2) key si format similaire (ex: "2026-02" ou "February 2026")
    # -> on tente juste un contains
    try:
        key_guess_1 = f"{now.year}-{now.month:02d}"
        p = qs.filter(key__icontains=key_guess_1).first()
        if p:
            return p
    except Exception:
        pass

    # 3) fallback dernière
    try:
        # si ordering existe déjà, .last() marche bien
        return qs.last()
    except Exception:
        return None


def build_secretary_overview(user):
    now = now_dt()
    current_period = _get_current_period(now)

    # ✅ Groups (MonthlyClassGroup) — base principale du dashboard
    groups_qs = (
        MonthlyClassGroup.objects
        .select_related("period", "level", "room")
        .filter(is_active=True)
    )
    if current_period:
        groups_qs = groups_qs.filter(period=current_period)

    # ✅ ordering VALID: level__order, group_name, room__code (Room a code ✅)
    groups_qs = groups_qs.order_by("level__order", "group_name", "room__code")

    groups = list(groups_qs[:50])

    # ✅ Assignments récents
    assignments = (
        TeacherCourseAssignment.objects
        .select_related(
            "teacher",
            "classroom",  # Room
            "course",
            "period",
            "monthly_group",
            "monthly_group__level",
            "monthly_group__room",
            "monthly_group__period",
        )
        .order_by("-created_at")[:20]
    )

    # ✅ KPIs
    overdue = Loan.objects.filter(
        returned_at__isnull=True,
        due_at__isnull=False,
        due_at__lt=now
    ).count()

    visitors_inside = GateEntry.objects.filter(check_out_at__isnull=True).count()

    # ✅ Alerts
    alerts = []
    if overdue:
        alerts.append({
            "type": "overdue",
            "title": "Overdue items",
            "message": f"{overdue} overdue item(s)",
        })

    # ✅ Return payload
    return {
        "kpis": [
            {
                "label": "Groups (current period)",
                "value": len(groups),
                "trend": current_period.key if current_period and hasattr(current_period, "key") else "",
            },
            {"label": "Overdue items", "value": overdue, "trend": "⚠️" if overdue else "OK"},
            {"label": "Visitors inside", "value": visitors_inside, "trend": ""},
        ],
        "lists": {
            "groups": [
                {
                    "id": g.id,
                    "period": getattr(getattr(g, "period", None), "key", "") or "",
                    "level": getattr(getattr(g, "level", None), "label", "") or "",
                    "group_name": g.group_name,
                    "room": getattr(getattr(g, "room", None), "code", "") or "",
                    "label": _group_label(g),
                    "is_active": bool(g.is_active),
                }
                for g in groups
            ],
            "recent_assignments": [
                {
                    "teacher": str(a.teacher),
                    "class": _assignment_class_label(a),
                    "course": str(a.course),
                    "is_titular": bool(a.is_titular),
                    "start_date": a.start_date.isoformat() if a.start_date else None,
                    "end_date": a.end_date.isoformat() if a.end_date else None,
                    "start_time": a.start_time.isoformat() if a.start_time else None,
                    "end_time": a.end_time.isoformat() if a.end_time else None,
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                }
                for a in assignments
            ],
        },
        "alerts": alerts,
    }
