# apps/attendance/qr.py
import hmac, hashlib
from django.conf import settings

PREFIX = "ABCR"
KIND_ROOM = "ROOM"

def _hmac(payload: str) -> str:
    return hmac.new(
        settings.SECRET_KEY.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()

# -------------------------
# ROOM QR / NFC (v2)
# -------------------------
def make_room_qr(room_code: str, tag_id: str) -> str:
    raw = f"{PREFIX}|{KIND_ROOM}|{room_code}|{tag_id}"
    sig = _hmac(raw)
    return f"{raw}|{sig}"

def parse_room_qr(qr_data: str) -> dict:
    s = (qr_data or "").strip()
    if not s:
        raise ValueError("Empty QR")

    # Simple formats
    if s.startswith("ROOM:"):
        code = s.replace("ROOM:", "", 1).strip()
        return {"room_code": code, "tag_id": None, "version": "ROOM"}

    parts = s.split("|")

    # v2: ABCR|ROOM|R1|tag_uuid|sig
    if len(parts) == 5 and parts[0] == PREFIX and parts[1] == KIND_ROOM:
        _, _, room_code, tag_id, sig = parts
        raw = f"{PREFIX}|{KIND_ROOM}|{room_code}|{tag_id}"
        expected = _hmac(raw)
        if not hmac.compare_digest(expected, sig):
            raise ValueError("Invalid room QR signature (v2)")
        return {"room_code": room_code, "tag_id": tag_id, "version": "ABCR_V2"}

    # v1 (legacy): ABCR|R1|sig
    if len(parts) == 3 and parts[0] == PREFIX:
        _, room_code, sig = parts
        expected = _hmac(room_code)
        if not hmac.compare_digest(expected, sig):
            raise ValueError("Invalid room QR signature (v1)")
        return {"room_code": room_code, "tag_id": None, "version": "ABCR_V1"}

    raise ValueError("Unsupported QR format")


# -------------------------
# GROUP QR (inchangé)
# -------------------------
def parse_group_qr(qr_data: str) -> dict:
    s = (qr_data or "").strip()
    if not s:
        raise ValueError("Empty QR")

    if s.startswith("GROUP:"):
        gid = int(s.replace("GROUP:", "", 1).strip())
        return {"group_id": gid, "period_key": None, "version": "GROUP"}

    parts = s.split("|")
    if len(parts) == 4 and parts[0] == "ABCGRP":
        _, gid, period_key, sig = parts
        payload = f"{gid}|{period_key}"
        expected = hmac.new(settings.SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, sig):
            raise ValueError("Invalid group QR signature")
        return {"group_id": int(gid), "period_key": period_key, "version": "ABCGRP"}

    raise ValueError("Unsupported group QR format")