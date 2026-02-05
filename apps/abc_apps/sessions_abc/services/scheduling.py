# =========================
# apps/sessions/services/scheduling.py
# =========================
from apps.abc_apps.sessions_abc.models import ClassSession, SessionTeacher
from apps.abc_apps.accounts.models import TeacherProfile
from apps.abc_apps.academics.models import ClassRoom

def create_session_with_teachers(
    classroom: ClassRoom,
    date,
    start_time,
    end_time,
    session_type: str,
    teacher_ids: list[int],
    created_by=None,
):
    session = ClassSession.objects.create(
        classroom=classroom,
        date=date,
        start_time=start_time,
        end_time=end_time,
        session_type=session_type,
        created_by=created_by,
    )
    teachers = TeacherProfile.objects.filter(id__in=teacher_ids)
    for t in teachers:
        SessionTeacher.objects.create(session=session, teacher=t, role_in_session="assistant")
    return session
