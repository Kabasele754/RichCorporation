# =========================================
# apps/dashboards/services/teacher.py
# =========================================
from django.utils import timezone
from apps.abc_apps.dashboards.services.utils import today_date, now_dt

from apps.abc_apps.sessions_abc.models import ClassSession, SessionTeacher
from apps.abc_apps.attendance.models import DailyRoomCheckIn
from apps.abc_apps.library.models import Loan
from apps.abc_apps.speeches.models import Speech

def build_teacher_overview(user):
    today = today_date()
    now = now_dt()

    # TeacherProfile assumed at user.teacher_profile
    tp = getattr(user, "teacher_profile", None)
    teacher_id = getattr(tp, "id", None)

    # Next / current sessions (based on SessionTeacher link)
    sessions = (
        ClassSession.objects
        .filter(date=today)
        .select_related("classroom")
        .order_by("start_time")
    )
    # If you store start_time/end_time in ClassSession; if not, it still works but ordering may fail.

    # Filter sessions taught by this teacher (via SessionTeacher)
    if teacher_id:
        my_session_ids = SessionTeacher.objects.filter(teacher_id=teacher_id, session__date=today).values_list("session_id", flat=True)
        sessions = sessions.filter(id__in=list(my_session_ids))

    # Attendance counts for first session (or current)
    session_cards = []
    for s in sessions[:6]:
        present = DailyRoomCheckIn.objects.filter(session=s).values("student_id").distinct().count()
        session_cards.append({
            "session_id": s.id,
            "class": f"{s.classroom.level}-{s.classroom.group_name}",
            "session_type": s.session_type,
            "present": present,
        })

    # My open loans (materials)
    my_open_loans = Loan.objects.select_related("item").filter(borrowed_by=user, returned_at__isnull=True).order_by("-borrowed_at")[:10]
    loans = [{
        "item_code": l.item.code,
        "title": l.item.title,
        "type": l.item.item_type,
        "due_at": l.due_at.isoformat() if l.due_at else None,
        "overdue": bool(l.due_at and l.due_at < now),
    } for l in my_open_loans]

    # Speeches to correct (simple heuristic: speeches created this month)
    speeches = Speech.objects.filter(created_at__date__month=today.month, created_at__date__year=today.year).order_by("-created_at")[:10]
    speech_list = [{"id": sp.id, "title": sp.title, "created_at": sp.created_at.isoformat()} for sp in speeches]

    alerts = []
    overdue_count = sum(1 for x in loans if x["overdue"])
    if overdue_count:
        alerts.append({"type": "overdue", "title": "Return materials", "message": f"{overdue_count} overdue item(s) to return"})

    return {
        "kpis": [
            {"label": "My sessions today", "value": sessions.count(), "trend": ""},
            {"label": "My open loans", "value": my_open_loans.count(), "trend": f"{overdue_count} overdue"},
        ],
        "cards": {
            "sessions": session_cards,
            "my_loans": loans,
            "speeches": speech_list,
        },
        "alerts": alerts,
    }
