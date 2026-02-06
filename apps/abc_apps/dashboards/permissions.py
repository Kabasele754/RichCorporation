# =========================================
# apps/dashboards/permissions.py
# =========================================
from rest_framework.permissions import BasePermission

def _role(user) -> str:
    return (getattr(user, "role", "") or "").lower().strip()

class IsPrincipal(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        if not (u and u.is_authenticated):
            return False
        if getattr(u, "is_superuser", False) or getattr(u, "is_staff", False):
            return True
        return _role(u) == "principal"

class IsSecretary(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        if not (u and u.is_authenticated):
            return False
        if getattr(u, "is_superuser", False) or getattr(u, "is_staff", False):
            return True
        return _role(u) == "secretary"

class IsTeacher(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        if not (u and u.is_authenticated):
            return False
        if getattr(u, "is_superuser", False) or getattr(u, "is_staff", False):
            return True
        return _role(u) == "teacher"

class IsSecurity(BasePermission):
    """
    Security agent:
    - group "Security" OR is_staff
    """
    def has_permission(self, request, view):
        u = request.user
        if not (u and u.is_authenticated):
            return False
        if getattr(u, "is_superuser", False) or getattr(u, "is_staff", False):
            return True
        try:
            return u.groups.filter(name__iexact="Security").exists()
        except Exception:
            return False

class IsPrincipalOrSecretary(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        if not (u and u.is_authenticated):
            return False
        if getattr(u, "is_superuser", False) or getattr(u, "is_staff", False):
            return True
        return _role(u) in ("principal", "secretary")
