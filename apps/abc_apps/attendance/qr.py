# apps/attendance/qr.py
import hmac, hashlib
from django.conf import settings

def parse_group_qr(qr_data: str) -> dict:
    s = (qr_data or "").strip()
    if not s:
        raise ValueError("Empty QR")

    # Simple
    if s.startswith("GROUP:"):
        gid = int(s.replace("GROUP:", "", 1).strip())
        return {"group_id": gid, "period_key": None, "version": "GROUP"}

    # Signed: ABCGRP|gid|period_key|sig
    parts = s.split("|")
    if len(parts) == 4 and parts[0] == "ABCGRP":
        _, gid, period_key, sig = parts
        payload = f"{gid}|{period_key}".encode()
        expected = hmac.new(settings.SECRET_KEY.encode(), payload, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, sig):
            raise ValueError("Invalid door QR signature")
        return {"group_id": int(gid), "period_key": period_key, "version": "ABCGRP"}

    raise ValueError("Unsupported door QR format")
