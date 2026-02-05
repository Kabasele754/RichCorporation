# =========================
# apps/attendance/services/scan.py
# =========================
from django.db import transaction
from django.utils import timezone

from apps.abc_apps.sessions_abc.services.qr import validate_payload
from apps.abc_apps.attendance.models import StudentAttendance, TeacherCheckIn, AttendanceConfirmation
from apps.abc_apps.accounts.models import StudentProfile, TeacherProfile
from apps.abc_apps.sessions_abc.models import SessionTeacher

def _teacher_assigned_to_session(session_id: int, teacher_id: int) -> bool:
    return SessionTeacher.objects.filter(session_id=session_id, teacher_id=teacher_id).exists()

@transaction.atomic
def student_scan(qr_payload: str, student: StudentProfile):
    token = validate_payload(qr_payload)
    session = token.session

    # ensure student belongs to the class (simple check by level/group)
    if student.current_level != session.classroom.level or student.group_name != session.classroom.group_name:
        raise ValueError("Student not in this class")

    att, created = StudentAttendance.objects.get_or_create(
        session=session,
        student=student,
        defaults={"scanned_at": timezone.now(), "status": "present", "scanned_by": "self_scan"},
    )
    return att, created

@transaction.atomic
def teacher_scan(qr_payload: str, teacher: TeacherProfile):
    token = validate_payload(qr_payload)
    session = token.session

    if not _teacher_assigned_to_session(session.id, teacher.id):
        raise ValueError("Teacher is not assigned to this session")

    checkin, _ = TeacherCheckIn.objects.get_or_create(
        session=session,
        teacher=teacher,
        defaults={"scanned_at": timezone.now(), "verified": True},
    )
    if not checkin.verified:
        checkin.verified = True
        checkin.save(update_fields=["verified"])
    return checkin

@transaction.atomic
def confirm_attendance(session_id: int, teacher: TeacherProfile, notes: str = ""):
    if not _teacher_assigned_to_session(session_id, teacher.id):
        raise ValueError("Teacher is not assigned to this session")

    conf, created = AttendanceConfirmation.objects.get_or_create(
        session_id=session_id,
        teacher=teacher,
        defaults={"confirmed_at": timezone.now(), "notes": notes},
    )
    if not created and notes:
        conf.notes = notes
        conf.save(update_fields=["notes"])
    return conf
