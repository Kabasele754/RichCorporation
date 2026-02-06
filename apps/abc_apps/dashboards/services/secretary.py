# =========================================
# apps/dashboards/services/secretary.py
# =========================================
from datetime import timedelta
from django.utils import timezone

from apps.abc_apps.dashboards.services.utils import today_date, now_dt
from apps.abc_apps.sessions_abc.models import ClassSession
from apps.abc_apps.academics.models import TeacherCourseAssignment
from apps.abc_apps.library.models import Loan
from apps.abc_apps.gate_security.models import GateEntry

def build_secretary_overview(user):
    today = today_date()
    now = now_dt()

    sessions_today = ClassSession.objects.select_related("classroom").filter(date=today).order_by("classroom__level", "classroom__group_name")
    assignments = TeacherCourseAssignment.objects.select_related("teacher", "classroom", "course").order_by("-created_at")[:20]

    overdue = Loan.objects.filter(returned_at__isnull=True, due_at__isnull=False, due_at__lt=now).count()
    visitors_inside = GateEntry.objects.filter(check_out_at__isnull=True).count()

    return {
        "kpis": [
            {"label": "Sessions today", "value": sessions_today.count(), "trend": ""},
            {"label": "Overdue items", "value": overdue, "trend": "⚠️" if overdue else "OK"},
            {"label": "Visitors inside", "value": visitors_inside, "trend": ""},
        ],
        "lists": {
            "sessions_today": [
                {"id": s.id, "class": f"{s.classroom.level}-{s.classroom.group_name}", "type": s.session_type}
                for s in sessions_today[:50]
            ],
            "recent_assignments": [
                {
                    "teacher": str(a.teacher),
                    "class": f"{a.classroom.level}-{a.classroom.group_name}",
                    "course": str(a.course),
                    "created_at": a.created_at.isoformat(),
                }
                for a in assignments
            ],
        },
        "alerts": [
            {"type": "overdue", "title": "Overdue items", "message": f"{overdue} overdue item(s)"} if overdue else None
        ],
    }
