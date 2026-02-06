# =========================================
# apps/dashboards/views.py
# =========================================
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from common.responses import ok, fail
from apps.abc_apps.dashboards.permissions import (
    IsPrincipal, IsSecretary, IsTeacher, IsSecurity, IsPrincipalOrSecretary
)
from apps.abc_apps.dashboards.services.principal import build_principal_overview
from apps.abc_apps.dashboards.services.security import build_security_overview
from apps.abc_apps.dashboards.services.teacher import build_teacher_overview
from apps.abc_apps.dashboards.services.secretary import build_secretary_overview

@api_view(["GET"])
@permission_classes([IsAuthenticated, IsPrincipal])
def principal_overview(request):
    try:
        days = int(request.query_params.get("days", "7"))
        days = max(3, min(days, 30))
        data = build_principal_overview(request.user, days=days)
        return ok(data)
    except Exception as e:
        return fail(str(e), status=400)

@api_view(["GET"])
@permission_classes([IsAuthenticated, IsSecurity])
def security_overview(request):
    try:
        data = build_security_overview(request.user)
        return ok(data)
    except Exception as e:
        return fail(str(e), status=400)

@api_view(["GET"])
@permission_classes([IsAuthenticated, IsTeacher])
def teacher_overview(request):
    try:
        data = build_teacher_overview(request.user)
        return ok(data)
    except Exception as e:
        return fail(str(e), status=400)

@api_view(["GET"])
@permission_classes([IsAuthenticated, IsPrincipalOrSecretary])
def secretary_overview(request):
    try:
        data = build_secretary_overview(request.user)
        return ok(data)
    except Exception as e:
        return fail(str(e), status=400)
