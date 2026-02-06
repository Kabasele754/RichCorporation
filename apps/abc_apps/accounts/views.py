# =========================
# apps/accounts/views.py
# =========================
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ViewSet
from rest_framework import status
from rest_framework_simplejwt.views import TokenObtainPairView


from apps.abc_apps.accounts.models import StudentProfile
from apps.abc_apps.accounts.serializers import AppTokenObtainPairSerializer, UserSerializer, StudentProfileSerializer, UpdateStudentLevelSerializer
from apps.abc_apps.accounts.permissions import IsSecretary, IsPrincipal
from apps.common.responses import fail, ok


class AppTokenObtainPairView(TokenObtainPairView):
    serializer_class = AppTokenObtainPairSerializer


class MeViewSet(ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["get"])
    def me(self, request):
        return ok(UserSerializer(request.user).data)

    @action(detail=False, methods=["get"])
    def my_student_profile(self, request):
        if not hasattr(request.user, "student_profile"):
            return fail("Not a student", status=404)
        return ok(StudentProfileSerializer(request.user.student_profile).data)

class SecretaryStudentAdminViewSet(ViewSet):
    permission_classes = [IsAuthenticated, (IsSecretary | IsPrincipal)]

    @action(detail=False, methods=["patch"])
    def update_level(self, request):
        ser = UpdateStudentLevelSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        sp = StudentProfile.objects.select_related("user").get(id=ser.validated_data["student_id"])
        sp.current_level = ser.validated_data["current_level"]
        sp.group_name = ser.validated_data["group_name"]
        if "status" in ser.validated_data:
            sp.status = ser.validated_data["status"]
        sp.save()
        return ok(StudentProfileSerializer(sp).data, message="Student level updated", status=status.HTTP_200_OK)
