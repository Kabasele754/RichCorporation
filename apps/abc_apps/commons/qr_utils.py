from __future__ import annotations
import hmac
import hashlib
from django.conf import settings


def parse_student_qr(qr_data: str) -> dict:
    """
    Supporte:
    - LEGACY: fullName|studentCode|level|groupName|validUntil|statusCode
    - ABC1:    ABC1|studentId|studentCode|validUntil|statusCode
    - ABC2:    ABC2|studentId|studentCode|validUntil|statusCode|sig  (HMAC)
    - ABCSTU:  ABCSTU:studentCode|studentId?
    - CODE:    studentCode only
    """
    s = (qr_data or "").strip()
    if not s:
        raise ValueError("Empty QR data")

    if s.startswith("ABCSTU:"):
        payload = s.replace("ABCSTU:", "", 1)
        parts = payload.split("|")
        student_code = parts[0].strip()
        student_id = int(parts[1]) if len(parts) >= 2 and parts[1].strip().isdigit() else None
        if not student_code:
            raise ValueError("Invalid student_code")
        return {"version": "ABCSTU", "student_id": student_id, "student_code": student_code}

    if "|" not in s:
        return {"version": "CODE", "student_id": None, "student_code": s}

    parts = s.split("|")

    if len(parts) == 5 and parts[0] == "ABC1":
        _, student_id, student_code, _, _ = parts
        return {"version": "ABC1", "student_id": int(student_id), "student_code": student_code.strip()}

    if len(parts) == 6 and parts[0] == "ABC2":
        _, student_id, student_code, valid_until, status_code, sig = parts
        payload = f"{student_id}|{student_code}|{valid_until}|{status_code}".encode()
        expected = hmac.new(settings.SECRET_KEY.encode(), payload, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, sig):
            raise ValueError("Invalid QR signature")
        return {"version": "ABC2", "student_id": int(student_id), "student_code": student_code.strip()}

    if len(parts) == 6:
        # LEGACY
        _, student_code, *_ = parts
        return {"version": "LEGACY", "student_id": None, "student_code": student_code.strip()}

    raise ValueError("Unsupported QR format")


def parse_room_qr(qr_data: str) -> dict:
    """
    QR statique porte (room).
    Format recommandé:
      ABCR1|<room_id>|<sig>
    sig = HMAC(SECRET_KEY, f"{room_id}")
    """
    s = (qr_data or "").strip()
    if not s:
        raise ValueError("Empty QR data")

    parts = s.split("|")
    if len(parts) != 3 or parts[0] != "ABCR1":
        raise ValueError("Unsupported room QR format")

    room_id = int(parts[1])
    sig = parts[2].strip()

    payload = f"{room_id}".encode()
    expected = hmac.new(settings.SECRET_KEY.encode(), payload, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected, sig):
        raise ValueError("Invalid room QR signature")

    return {"version": "ABCR1", "room_id": room_id}
