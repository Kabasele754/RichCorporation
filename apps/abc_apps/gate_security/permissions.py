# =========================================
# apps/abc_apps/gate_security/permissions.py
# =========================================
from rest_framework.permissions import BasePermission

class IsSecurityOrStaff(BasePermission):
    """
    Autorise:
    - user.is_staff (super simple)
    - OU user.role in (secretary, principal, teacher) si tu veux aussi leur permettre
    - OU user appartient au groupe "Security"
    """

    def has_permission(self, request, view):
        u = request.user
        if not (u and u.is_authenticated):
            return False

        if getattr(u, "is_staff", False):
            return True

        role = getattr(u, "role", "")
        if role in ("secretary", "principal", "teacher"):
            return True

        try:
            return u.groups.filter(name__iexact="Security").exists()
        except Exception:
            return False
