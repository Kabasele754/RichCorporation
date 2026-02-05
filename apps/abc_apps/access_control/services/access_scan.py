# =========================================
# apps/abc_apps/access_control/services/access_scan.py
# =========================================
from django.utils import timezone

from apps.abc_apps.access_control.models import Credential, AccessRule, AccessLog, AccessPoint
from apps.abc_apps.gate_security.models import GateEntry

def _role(user) -> str:
    return getattr(user, "role", "") or ""

def _time_allowed(rule: AccessRule) -> bool:
    if not rule.start_time or not rule.end_time:
        return True
    now_t = timezone.localtime().time()
    return rule.start_time <= now_t <= rule.end_time

def _check_access_rule(access_point: AccessPoint, role: str):
    """
    Si aucune règle n'existe => on autorise (mode simple).
    Si des règles existent => appliquer allow/deny.
    """
    rules = AccessRule.objects.filter(access_point=access_point, role=role)
    if not rules.exists():
        return True, "OK (no rule)"

    # si une règle deny existe et s'applique => deny
    for r in rules:
        if _time_allowed(r) and not r.allow:
            return False, "Access denied by rule"

    # si au moins une allow qui s'applique => allow
    for r in rules:
        if _time_allowed(r) and r.allow:
            return True, "OK (rule)"

    return False, "Access denied (rule time window)"

def resolve_identity(uid: str):
    """
    Retourne: (user, visitor_entry, method_guess)
    - user si Credential trouvé
    - visitor_entry si GateEntry.access_uid trouvé et open
    """
    cred = Credential.objects.select_related("user").filter(uid=uid, status="active").first()
    if cred:
        method_guess = cred.cred_type
        return cred.user, None, method_guess

    entry = GateEntry.objects.filter(access_uid=uid, check_out_at__isnull=True).first()
    if entry:
        return None, entry, "qr"

    return None, None, None

def check_student_class_match(user, access_point: AccessPoint):
    """
    Règle: un student F1 ne peut pas scanner dans INT2, etc.
    => si access_point.classroom est défini: student.current_level & group_name doivent matcher.
    """
    role = _role(user)
    if role != "student":
        return True, "OK"

    if access_point.point_type != "room_door":
        return True, "OK"

    if not access_point.classroom:
        return True, "OK (no classroom on access point)"

    sp = getattr(user, "student_profile", None)
    if not sp:
        return False, "Student profile missing"

    if sp.current_level != access_point.classroom.level or sp.group_name != access_point.classroom.group_name:
        return False, "Access denied: wrong class/level"

    return True, "OK"

def process_scan(uid: str, access_point: AccessPoint, method: str = "qr"):
    """
    1) Identify (user or visitor)
    2) Apply student classroom restriction
    3) Apply AccessRule (optional)
    4) Create AccessLog
    """
    user, visitor_entry, method_guess = resolve_identity(uid)
    if method in ("qr", "nfc", "manual"):
        scan_method = method
    else:
        scan_method = method_guess or "qr"

    if not access_point.is_active:
        log = AccessLog.objects.create(
            access_point=access_point, user=user, visitor_entry=visitor_entry,
            method=scan_method, uid=uid, allowed=False, reason="Access point inactive"
        )
        return False, "Access point inactive", log

    # Unknown badge
    if not user and not visitor_entry:
        log = AccessLog.objects.create(
            access_point=access_point, method=scan_method, uid=uid,
            allowed=False, reason="Unknown badge/UID"
        )
        return False, "Unknown badge/UID", log

    # Visitor: allow by default, but you can add rules if needed
    if visitor_entry and not user:
        allowed, reason = _check_access_rule(access_point, "visitor")
        log = AccessLog.objects.create(
            access_point=access_point, visitor_entry=visitor_entry,
            method=scan_method, uid=uid, allowed=allowed, reason=reason
        )
        return allowed, reason, log

    # Known user
    role = _role(user)

    # Student restriction: must match the classroom for room_door
    ok_class, class_reason = check_student_class_match(user, access_point)
    if not ok_class:
        log = AccessLog.objects.create(
            access_point=access_point, user=user,
            method=scan_method, uid=uid, allowed=False, reason=class_reason
        )
        return False, class_reason, log

    # Apply AccessRule (optional)
    allowed, reason = _check_access_rule(access_point, role or "staff")

    log = AccessLog.objects.create(
        access_point=access_point,
        user=user,
        method=scan_method,
        uid=uid,
        allowed=allowed,
        reason=reason,
    )
    return allowed, reason, log
