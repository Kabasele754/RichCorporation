# =========================
# apps/sessions/services/qr.py
# =========================
from datetime import timedelta
from django.utils import timezone
from commons.utils import make_token
from apps.abc_apps.sessions_abc.models import AttendanceToken, ClassSession

DEFAULT_TTL_MINUTES = 180  # 3h (tu peux changer)

def generate_or_refresh_token(session: ClassSession, ttl_minutes: int = DEFAULT_TTL_MINUTES) -> AttendanceToken:
    expires = timezone.now() + timedelta(minutes=ttl_minutes)
    token, created = AttendanceToken.objects.get_or_create(
        session=session,
        defaults={"qr_payload": make_token(40), "expires_at": expires},
    )
    if not created:
        token.expires_at = expires
        if not token.qr_payload:
            token.qr_payload = make_token(40)
        token.save(update_fields=["qr_payload", "expires_at"])
    return token

def validate_payload(payload: str) -> AttendanceToken:
    token = AttendanceToken.objects.select_related("session").get(qr_payload=payload)
    if not token.is_valid():
        raise ValueError("QR token expired")
    return token
