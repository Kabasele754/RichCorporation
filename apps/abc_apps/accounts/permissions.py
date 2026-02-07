from rest_framework.permissions import BasePermission


class IsPrincipal(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.role == "principal")


class IsSecretary(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.role == "secretary")


class IsTeacher(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.role == "teacher")


class IsStudent(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.role == "student")


class IsSecurity(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.role == "security")


class IsStaffABC(BasePermission):
    """
    Staff = principal/secretary/teacher/security
    """
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.role in ["principal", "secretary", "teacher", "security"])
