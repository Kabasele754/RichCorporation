# =========================================
# apps/dashboards/services/security.py
# =========================================
from datetime import timedelta
from django.utils import timezone

from apps.abc_apps.dashboards.services.utils import today_date, now_dt
from apps.abc_apps.gate_security.models import GateEntry
from apps.abc_apps.access_control.models import AccessLog

def build_security_overview(user):
    today = today_date()
    now = now_dt()

    open_entries = GateEntry.objects.filter(check_out_at__isnull=True).order_by("-check_in_at")
    visitors_inside = open_entries.count()
    overstays = open_entries.filter(check_in_at__lte=now - timedelta(minutes=30)).count()

    # last 20 door scans today (optional)
    scans_today = (
        AccessLog.objects
        .select_related("access_point", "user", "visitor_entry")
        .filter(scanned_at__date=today)
        .order_by("-scanned_at")[:20]
    )

    scan_list = []
    for log in scans_today:
        who = ""
        role = ""
        if log.user:
            who = (f"{log.user.first_name} {log.user.last_name}").strip() or log.user.username
            role = getattr(log.user, "role", "") or ""
        elif log.visitor_entry:
            who = log.visitor_entry.full_name
            role = "visitor"

        scan_list.append({
            "time": timezone.localtime(log.scanned_at).strftime("%H:%M"),
            "who": who,
            "role": role,
            "point": str(log.access_point) if log.access_point else "",
            "allowed": log.allowed,
            "reason": log.reason,
        })

    alerts = []
    if overstays:
        alerts.append({"type": "overstay", "title": "Overstays", "message": f"{overstays} person(s) > 30 min"})

    return {
        "kpis": [
            {"label": "People inside", "value": visitors_inside, "trend": ""},
            {"label": "Overstays >30min", "value": overstays, "trend": "⚠️" if overstays else "OK"},
        ],
        "lists": {
            "open_gate_entries": [
                {
                    "id": e.id,
                    "name": e.full_name,
                    "type": e.person_type,
                    "purpose": e.purpose,
                    "check_in": timezone.localtime(e.check_in_at).strftime("%H:%M"),
                    "over_30": e.check_in_at <= now - timedelta(minutes=30),
                }
                for e in open_entries[:30]
            ],
            "recent_scans": scan_list,
        },
        "alerts": alerts,
    }
