# =========================
# apps/accounts/views.py
# =========================
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ViewSet
from rest_framework import status
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.abc_apps.accounts.models import StudentProfile
from apps.abc_apps.accounts.serializers import AppTokenObtainPairSerializer, ChangePasswordSerializer, LogoutSerializer, MeSerializer, MeUpdateSerializer, UserSerializer, StudentProfileSerializer, UpdateStudentLevelSerializer
from apps.abc_apps.accounts.permissions import IsSecretary, IsPrincipal
from apps.common.responses import fail, ok

from rest_framework.views import APIView
from rest_framework import status, permissions
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import AllowAny
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from rest_framework import generics


class AppTokenObtainPairView(TokenObtainPairView):
    serializer_class = AppTokenObtainPairSerializer
    
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    data = MeSerializer(request.user).data
    return ok(data)


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



@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def me_update(request):
    ser = MeUpdateSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    data = ser.validated_data

    u = request.user

    # ✅ update user fields
    if "first_name" in data:
        u.first_name = data["first_name"]
    if "last_name" in data:
        u.last_name = data["last_name"]
    if "email" in data:
        u.email = data["email"]
    u.save()

    # ✅ update profile based on role
    role = getattr(u, "role", "student")

    if role == "student" and hasattr(u, "student_profile"):
        sp = u.student_profile
        if "current_level" in data:
            sp.current_level = data["current_level"]
        if "group_name" in data:
            sp.group_name = data["group_name"]
        sp.save()

    elif role == "teacher" and hasattr(u, "teacher_profile"):
        tp = u.teacher_profile
        if "speciality" in data:
            tp.speciality = data["speciality"]
        tp.save()

    elif role == "security" and hasattr(u, "security_profile"):
        sec = u.security_profile
        if "shifts" in data:
            sec.shifts = data["shifts"]
        sec.save()

    # secretary/principal usually only update user basic fields

    return ok(MeSerializer(u).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def change_password(request):
    ser = ChangePasswordSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    data = ser.validated_data

    u = request.user

    if not u.check_password(data["old_password"]):
        return Response({"detail": "Old password is incorrect."}, status=status.HTTP_400_BAD_REQUEST)

    u.set_password(data["new_password"])
    u.save()

    return ok({"message": "Password updated successfully."})


class LogoutAPIView(generics.GenericAPIView):
    serializer_class = LogoutSerializer
    permission_classes = (IsAuthenticated,)
    parser_classes = (JSONParser, FormParser, MultiPartParser)

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'msg':'Logout Success'}, status=status.HTTP_200_OK)
            
            
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
