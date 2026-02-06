# =========================
# apps/accounts/permissions.py
# =========================
from apps.common.permissions import IsStudent, IsTeacher, IsSecretary, IsPrincipal, IsStaffOrPrincipal
# re-export (clean import for views)
__all__ = ["IsStudent", "IsTeacher", "IsSecretary", "IsPrincipal", "IsStaffOrPrincipal"]
