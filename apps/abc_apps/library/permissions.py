# =========================================
# apps/library/permissions.py
# =========================================
from rest_framework.permissions import BasePermission

class IsTeacherOrSecretaryOrStaff(BasePermission):
    """
    Pour emprunter/rendre au desk (teacher/secretary/security staff).
    Students peuvent aussi emprunter, mais selon ton choix.
    """
    def has_permission(self, request, view):
        u = request.user
        if not (u and u.is_authenticated):
            return False

        if getattr(u, "is_staff", False):
            return True

        role = getattr(u, "role", "")
        return role in ("teacher", "secretary", "principal")
