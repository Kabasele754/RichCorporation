# =========================
# apps/accounts/urls.py
# =========================
from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework.routers import DefaultRouter
from apps.abc_apps.accounts.views import AppTokenObtainPairView, LogoutAPIView, MeViewSet, SecretaryStudentAdminViewSet, SecretaryTeacherViewSet, change_password, me, me_update

router = DefaultRouter()
router.register(r"me", MeViewSet, basename="me")
router.register(r"secretary/students", SecretaryStudentAdminViewSet, basename="secretary-students")
router.register(r"secretary", SecretaryTeacherViewSet, basename="secretary")

urlpatterns = [
    path("", include(router.urls)),
    path("auth/login/", AppTokenObtainPairView.as_view(), name="auth-login"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="auth-refresh"),
    path("auth/me/", me, name="auth-me"),
    path("auth/me/update/", me_update, name="auth-me-update"),
    path("auth/change-password/", change_password, name="auth-change-password"),
    path("auth/logout/", LogoutAPIView.as_view(), name="logout"),
]
