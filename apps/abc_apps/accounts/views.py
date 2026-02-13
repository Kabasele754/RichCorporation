# =========================
# apps/accounts/views.py
# =========================
from django.db.models import Q
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ViewSet
from rest_framework import status
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.abc_apps.accounts.models import StudentProfile, TeacherProfile
from apps.abc_apps.accounts.serializers import AppTokenObtainPairSerializer, ArchiveStudentSerializer, ChangePasswordSerializer, LogoutSerializer, MeSerializer, MeUpdateSerializer, TeacherCreateSerializer, TeacherListSerializer, UserSerializer, StudentProfileSerializer, UpdateStudentLevelSerializer
from apps.abc_apps.accounts.permissions import IsSecretary, IsPrincipal
from apps.common.permissions import IsStaffOrPrincipal
from apps.common.responses import fail, ok

from rest_framework.views import APIView
from rest_framework import status, permissions
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import AllowAny
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from rest_framework import generics
from rest_framework.pagination import PageNumberPagination


def ok(data=None, message="OK", status=status.HTTP_200_OK):
    return Response({"message": message, "data": data}, status=status)

def bad(message="Bad request", status=status.HTTP_400_BAD_REQUEST):
    return Response({"message": message}, status=status)


class StudentPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


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
    pagination_class = StudentPagination

    def get_queryset(self):
        return StudentProfile.objects.select_related("user").order_by("-created_at")

    # ✅ 1) LISTE DES STUDENTS
    # GET /api/secretary/students/?level=L1&group=A&status=ACTIVE&search=paul&page=1&page_size=20
    def list(self, request):
        qs = self.get_queryset()

        level = request.query_params.get("level")
        group = request.query_params.get("group")
        st = request.query_params.get("status")
        search = request.query_params.get("search")

        if level:
            qs = qs.filter(current_level=level)
        if group:
            qs = qs.filter(group_name=group)
        if st:
            qs = qs.filter(status=st)

        if search:
            qs = qs.filter(
                Q(user__first_name__icontains=search)
                | Q(user__last_name__icontains=search)
                | Q(user__email__icontains=search)
                | Q(student_code__icontains=search)
            )

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        data = StudentProfileSerializer(page, many=True).data
        return paginator.get_paginated_response(data)

    # ✅ 2) DETAIL (optionnel mais utile)
    # GET /api/secretary/students/{id}/
    def retrieve(self, request, pk=None):
        sp = self.get_queryset().get(id=pk)
        return ok(StudentProfileSerializer(sp).data)

    # ✅ 3) UPDATE LEVEL (ton endpoint)
    # PATCH /api/secretary/students/update_level/
    @action(detail=False, methods=["patch"])
    def update_level(self, request):
        ser = UpdateStudentLevelSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        sp = self.get_queryset().get(id=ser.validated_data["student_id"])
        sp.current_level = ser.validated_data["current_level"]
        sp.group_name = ser.validated_data["group_name"]
        if "status" in ser.validated_data:
            sp.status = ser.validated_data["status"]
        sp.save()

        return ok(StudentProfileSerializer(sp).data, message="Student level updated", status=status.HTTP_200_OK)

    # ✅ 4) ARCHIVE / RESTORE
    # PATCH /api/secretary/students/archive/
    # body: {"student_id": 12, "status": "ARCHIVED"}
    @action(detail=False, methods=["patch"])
    def archive(self, request):
        ser = ArchiveStudentSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        sp = self.get_queryset().get(id=ser.validated_data["student_id"])
        sp.status = ser.validated_data["status"]
        sp.save()

        return ok(StudentProfileSerializer(sp).data, message="Student status updated", status=status.HTTP_200_OK) 


class SecretaryTeacherViewSet(ViewSet):
    permission_classes = [IsAuthenticated, (IsSecretary | IsStaffOrPrincipal)]

    # ✅ GET /api/secretary/teachers/?q=...
    @action(detail=False, methods=["get"])
    def teachers(self, request):
        q = request.query_params.get("q", "").strip()

        qs = TeacherProfile.objects.select_related("user")

        # ✅ filtre (search)
        if q:
            qs = qs.filter(
                Q(user__username__icontains=q) |
                Q(user__first_name__icontains=q) |
                Q(user__last_name__icontains=q) |
                Q(user__email__icontains=q) |
                Q(teacher_code__icontains=q) |
                Q(speciality__icontains=q)
            )

        qs = qs.order_by("user__last_name", "user__first_name")
        ser = TeacherListSerializer(qs, many=True)

        # ✅ ton wrapper ok() renvoie déjà {data: ...}
        return ok(ser.data, message="Teachers list", status=status.HTTP_200_OK)

    # ✅ POST /api/secretary/create_teacher/
    @action(detail=False, methods=["post"])
    def create_teacher(self, request):
        ser = TeacherCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        user = ser.save()  # ⚠️ IMPORTANT : doit retourner User (pas tuple)

        return ok(
            {
                "user_id": user.id,
                "username": user.username,
                "full_name": user.get_full_name() or user.username,
                "role": getattr(user, "role", "teacher"),
                "default_password": "abc1234" if not request.data.get("password") else None,
            },
            message="Teacher created successfully",
            status=status.HTTP_201_CREATED,
        )
        
        
            
