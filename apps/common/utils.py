# =========================
# common/utils.py
# =========================
import secrets

def make_token(length=32) -> str:
    # URL-safe random token
    return secrets.token_urlsafe(length)[:length]
