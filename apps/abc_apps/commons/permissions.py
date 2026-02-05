# =========================
# common/permissions.py
# =========================
from rest_framework.permissions import BasePermission

def _role(user):
    return getattr(user, "role", None)

class IsStudent(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and _role(request.user) == "student")

class IsTeacher(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and _role(request.user) == "teacher")

class IsSecretary(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and _role(request.user) == "secretary")

class IsPrincipal(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and _role(request.user) == "principal")

class IsStaffOrPrincipal(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated
            and (_role(request.user) in ("teacher", "secretary", "principal") or request.user.is_staff)
        )
