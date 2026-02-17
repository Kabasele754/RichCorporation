# apps/attendance/qr.py
from __future__ import annotations
import hmac, hashlib
from django.conf import settings

QR_PREFIX_SIGNED = "ABCGRP"
QR_PREFIX_SIMPLE = "GROUP:"

def _sig(payload: str) -> str:
    return hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

def make_group_qr_static(group_id: int, signed: bool = True) -> str:
    if not group_id or int(group_id) <= 0:
        raise ValueError("group_id must be positive")

    gid = int(group_id)

    if not signed:
        return f"{QR_PREFIX_SIMPLE}{gid}"

    payload = f"{gid}"
    sig = _sig(payload)
    return f"{QR_PREFIX_SIGNED}|{gid}|{sig}"

def parse_group_qr_static(qr_data: str) -> dict:
    s = (qr_data or "").strip()
    if not s:
        raise ValueError("Empty QR")

    # Simple
    if s.startswith(QR_PREFIX_SIMPLE):
        gid_str = s.replace(QR_PREFIX_SIMPLE, "", 1).strip()
        if not gid_str.isdigit():
            raise ValueError("Invalid GROUP id")
        return {"group_id": int(gid_str), "version": "GROUP"}

    # Signed: ABCGRP|gid|sig
    parts = s.split("|")
    if len(parts) == 3 and parts[0] == QR_PREFIX_SIGNED:
        _, gid, sig = parts
        if not gid.isdigit():
            raise ValueError("Invalid group_id in QR")

        payload = f"{int(gid)}"
        expected = _sig(payload)
        if not hmac.compare_digest(expected, sig):
            raise ValueError("Invalid QR signature")

        return {"group_id": int(gid), "version": "ABCGRP"}

    raise ValueError("Unsupported QR format")
