# =========================================
# apps/dashboards/urls.py
# =========================================
from django.urls import path
from apps.abc_apps.dashboards.views import (
    principal_overview,
    security_overview,
    teacher_overview,
    secretary_overview,
)

urlpatterns = [
    path("principal/overview/", principal_overview, name="dashboard-principal-overview"),
    path("security/overview/", security_overview, name="dashboard-security-overview"),
    path("teacher/overview/", teacher_overview, name="dashboard-teacher-overview"),
    path("secretary/overview/", secretary_overview, name="dashboard-secretary-overview"),
]
