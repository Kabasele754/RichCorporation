# =========================================
# apps/dashboards/services/secretary.py
# =========================================
from django.db.models import F
from apps.abc_apps.dashboards.services.utils import today_date, now_dt
from apps.abc_apps.sessions_abc.models import ClassSession
from apps.abc_apps.academics.models import TeacherCourseAssignment
from apps.abc_apps.library.models import Loan
from apps.abc_apps.gate_security.models import GateEntry


def _group_label(g):
    # g: MonthlyClassGroup
    # ex: "Foundation 1 A • R2"
    try:
        return g.label
    except Exception:
        return f"{getattr(g.level, 'label', '')} {g.group_name} • {getattr(g.room, 'code', '')}".strip()


def _assignment_class_label(a: TeacherCourseAssignment) -> str:
    """
    Priorité:
    1) monthly_group.label (level + group + room)
    2) room code/name
    """
    if getattr(a, "monthly_group", None):
        return _group_label(a.monthly_group)

    room = getattr(a, "classroom", None)  # classroom = Room
    if room:
        return f"{room.code} • {room.name}"
    return "—"


def _session_class_label(s: ClassSession) -> str:
    """
    Selon ton modèle actuel, ClassSession a classroom=Room.
    Donc on affiche Room.
    Si plus tard tu ajoutes monthly_group sur ClassSession, on l’utilisera.
    """
    mg = getattr(s, "monthly_group", None)
    if mg:
        return _group_label(mg)

    room = getattr(s, "classroom", None)
    if room:
        return f"{room.code} • {room.name}"
    return "—"


def build_secretary_overview(user):
    today = today_date()
    now = now_dt()

    # ✅ Sessions today (ClassSession -> classroom=Room)
    # IMPORTANT: si tu as "monthly_group" dans ClassSession, ajoute le select_related
    sessions_today = (
        ClassSession.objects
        .select_related("classroom")  # + ("monthly_group", "monthly_group__level", "monthly_group__room") si existe
        .filter(date=today)
        .order_by("classroom__code")  # Room.ordering = ["code"]
    )

    # ✅ Assignments: on utilise monthly_group si présent
    assignments = (
        TeacherCourseAssignment.objects
        .select_related(
            "teacher",
            "classroom",  # Room
            "course",
            "monthly_group",
            "monthly_group__level",
            "monthly_group__room",
            "monthly_group__period",
        )
        .order_by("-created_at")[:20]
    )

    overdue = Loan.objects.filter(
        returned_at__isnull=True,
        due_at__isnull=False,
        due_at__lt=now
    ).count()

    visitors_inside = GateEntry.objects.filter(check_out_at__isnull=True).count()

    alerts = []
    if overdue:
        alerts.append({
            "type": "overdue",
            "title": "Overdue items",
            "message": f"{overdue} overdue item(s)",
        })

    return {
        "kpis": [
            {"label": "Sessions today", "value": sessions_today.count(), "trend": ""},
            {"label": "Overdue items", "value": overdue, "trend": "⚠️" if overdue else "OK"},
            {"label": "Visitors inside", "value": visitors_inside, "trend": ""},
        ],
        "lists": {
            "sessions_today": [
                {
                    "id": s.id,
                    "class": _session_class_label(s),
                    "type": getattr(s, "session_type", ""),
                }
                for s in sessions_today[:50]
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
