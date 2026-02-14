from __future__ import annotations

from datetime import date, timedelta
import hmac
import hashlib

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from rest_framework.viewsets import ViewSet, ModelViewSet
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

# ✅ tes models existants (adapte les imports)
from apps.abc_apps.academics.models import (
    TeacherCourseAssignment,
    MonthlyClassGroup,
    StudentMonthlyEnrollment,
    StudentProfile,
)
from apps.abc_apps.academics.serializers import StudentMonthlyEnrollmentSerializer, TeacherCourseAssignmentSerializer
from apps.common.permissions import IsTeacher

from .models import ClassGeneralRemark, StudentMonthlyObjective, StudentProofScan, StudentRemark, WeeklyTeachingPlan, Homework, HomeworkSubmission
from .serializers import (
    ClassGeneralRemarkSerializer,
    StudentMonthlyObjectiveSerializer,
    StudentProofScanSerializer,
    StudentRemarkSerializer,
    StudentMiniSerializer,
    WeeklyTeachingPlanSerializer,
    HomeworkSerializer,
    HomeworkSubmissionSerializer,
    EnrollByQrPayloadSerializer,
)

# ---------------------------
# Helpers
# ---------------------------
def ok(data=None, message="OK", status_code=status.HTTP_200_OK):
    return Response({"message": message, "data": data}, status=status_code)

def bad(message="Bad request", status_code=status.HTTP_400_BAD_REQUEST):
    return Response({"message": message}, status=status_code)

def monday_of(d: date) -> date:
    return d - timedelta(days=d.weekday())

def parse_qr_data(qr_data: str) -> dict:
    """
    Supporte:
    - LEGACY: fullName|studentCode|level|groupName|validUntil|statusCode
    - ABC1:    ABC1|studentId|studentCode|validUntil|statusCode
    - ABC2:    ABC2|studentId|studentCode|validUntil|statusCode|sig  (HMAC)
    """
    parts = qr_data.split("|")

    # ABC1
    if len(parts) == 5 and parts[0] == "ABC1":
        _, student_id, student_code, valid_until, status_code = parts
        return {
            "version": "ABC1",
            "student_id": int(student_id),
            "student_code": student_code.strip(),
            "valid_until": valid_until.strip(),
            "status_code": status_code.strip().lower(),
        }

    # ABC2 (signed)
    if len(parts) == 6 and parts[0] == "ABC2":
        _, student_id, student_code, valid_until, status_code, sig = parts
        payload = f"{student_id}|{student_code}|{valid_until}|{status_code}".encode()

        expected = hmac.new(
            key=settings.SECRET_KEY.encode(),
            msg=payload,
            digestmod=hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(expected, sig):
            raise ValueError("Invalid QR signature")

        return {
            "version": "ABC2",
            "student_id": int(student_id),
            "student_code": student_code.strip(),
            "valid_until": valid_until.strip(),
            "status_code": status_code.strip().lower(),
        }

    # LEGACY
    if len(parts) == 6:
        full_name, student_code, level, group_name, valid_until, status_code = parts
        return {
            "version": "LEGACY",
            "student_id": None,
            "student_code": student_code.strip(),
            "valid_until": valid_until.strip(),
            "status_code": status_code.strip().lower(),
        }

    raise ValueError("Unsupported QR format")


# ---------------------------
# 1) Teacher Schedule
# ---------------------------
class TeacherScheduleViewSet(ViewSet):
    permission_classes = [IsAuthenticated, IsTeacher]

    def list(self, request):
        teacher = request.user.teacher_profile

        period_key = request.query_params.get("period")      # ex: 2026-02
        monthly_group_id = request.query_params.get("monthly_group")

        qs = TeacherCourseAssignment.objects.select_related(
            "teacher__user", "course", "classroom", "period", "monthly_group"
        ).filter(teacher=teacher)

        if period_key:
            qs = qs.filter(period__key=period_key)
        if monthly_group_id:
            qs = qs.filter(monthly_group_id=monthly_group_id)

        return ok(TeacherCourseAssignmentSerializer(qs, many=True).data)


# ---------------------------
# 2) Teacher Classes + details (one shot)
# ---------------------------
class TeacherClassViewSet(ViewSet):
    permission_classes = [IsAuthenticated, IsTeacher]

    def list(self, request):
        teacher = request.user.teacher_profile

        qs = TeacherCourseAssignment.objects.select_related(
            "monthly_group__level",
            "monthly_group__room",
            "period",
            "course",
        ).filter(
            teacher=teacher,
            monthly_group__isnull=False
        ).order_by("-period__year", "-period__month")

        groups = {}
        for a in qs:
            g = a.monthly_group
            if g.id not in groups:
                groups[g.id] = {
                    "id": g.id,
                    "label": g.label,
                    "period": a.period.key if a.period else None,
                    "level": g.level.label,
                    "group_name": g.group_name,
                    "room": g.room.code,
                    "is_active": g.is_active,
                }

        return ok(list(groups.values()))

    @action(detail=True, methods=["get"])
    def details(self, request, pk=None):
        """
        GET /api/teacher/classes/{group_id}/details/?week_start=YYYY-MM-DD
        """
        teacher = request.user.teacher_profile

        if not TeacherCourseAssignment.objects.filter(teacher=teacher, monthly_group_id=pk).exists():
            return bad("Not allowed", status_code=status.HTTP_403_FORBIDDEN)

        week_start_str = request.query_params.get("week_start")
        if week_start_str:
            try:
                week_start = monday_of(date.fromisoformat(week_start_str))
            except ValueError:
                return bad("week_start must be YYYY-MM-DD", status_code=status.HTTP_400_BAD_REQUEST)
        else:
            week_start = monday_of(date.today())

        group = MonthlyClassGroup.objects.select_related("period", "level", "room").get(id=pk)

        group_data = {
            "id": group.id,
            "label": group.label,
            "period": group.period.key,
            "level": group.level.label,
            "group_name": group.group_name,
            "room": group.room.code,
            "is_active": group.is_active,
        }

        assignments = TeacherCourseAssignment.objects.select_related(
            "teacher__user", "course", "classroom", "period", "monthly_group"
        ).filter(teacher=teacher, monthly_group_id=pk)

        courses_data = TeacherCourseAssignmentSerializer(assignments, many=True).data

        enrolls = StudentMonthlyEnrollment.objects.select_related("student__user").filter(
            group_id=pk, status="active"
        ).order_by("student__user__first_name", "student__user__last_name")

        students = [e.student for e in enrolls]
        students_data = StudentMiniSerializer(students, many=True).data

        course_ids = list(assignments.values_list("course_id", flat=True).distinct())

        plans = WeeklyTeachingPlan.objects.filter(
            teacher=teacher,
            monthly_group_id=pk,
            course_id__in=course_ids,
            week_start=week_start,
        ).select_related("course")

        plan_by_course_id = {p.course_id: p for p in plans}

        weekly_plans_data = []
        for a in assignments:
            p = plan_by_course_id.get(a.course_id)
            weekly_plans_data.append({
                "course_id": a.course_id,
                "course_name": a.course.name,
                "plan": WeeklyTeachingPlanSerializer(p).data if p else None,
            })

        return ok({
            "group": group_data,
            "week_start": week_start.isoformat(),
            "courses": courses_data,
            "students": students_data,
            "weekly_plans": weekly_plans_data,
        })


# ---------------------------
# 3) Weekly plans CRUD
# ---------------------------
class TeacherWeeklyPlanViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated, IsTeacher]
    serializer_class = WeeklyTeachingPlanSerializer
    queryset = WeeklyTeachingPlan.objects.all()

    def get_queryset(self):
        teacher = self.request.user.teacher_profile
        qs = super().get_queryset().filter(teacher=teacher)

        monthly_group = self.request.query_params.get("monthly_group")
        week_start = self.request.query_params.get("week_start")

        if monthly_group:
            qs = qs.filter(monthly_group_id=monthly_group)
        if week_start:
            qs = qs.filter(week_start=week_start)

        return qs.order_by("-week_start", "-created_at")

    def perform_create(self, serializer):
        teacher = self.request.user.teacher_profile

        monthly_group = serializer.validated_data["monthly_group"]
        course = serializer.validated_data["course"]
        week_start = monday_of(serializer.validated_data["week_start"])

        if not TeacherCourseAssignment.objects.filter(
            teacher=teacher,
            monthly_group=monthly_group,
            course=course
        ).exists():
            raise ValueError("Not assigned to this course/class.")

        serializer.save(
            teacher=teacher,
            period=monthly_group.period,
            week_start=week_start
        )


# ---------------------------
# 4) QR Enrollment endpoint
# ---------------------------
class TeacherQrEnrollmentViewSet(ViewSet):
    permission_classes = [IsAuthenticated, IsTeacher]

    @action(detail=False, methods=["post"])
    def enroll(self, request):
        """
        POST /api/teacher/enrollments/enroll/
        body: {"group_id": 5, "qr_data": "...", "status":"active"}
        """
        ser = EnrollByQrPayloadSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        teacher = request.user.teacher_profile
        group = MonthlyClassGroup.objects.select_related("period").get(id=ser.validated_data["group_id"])

        if not TeacherCourseAssignment.objects.filter(teacher=teacher, monthly_group=group).exists():
            return bad("Not allowed", status_code=status.HTTP_403_FORBIDDEN)

        try:
            parsed = parse_qr_data(ser.validated_data["qr_data"])
        except ValueError as e:
            return bad(str(e), status_code=status.HTTP_400_BAD_REQUEST)

        if parsed.get("student_id"):
            student = StudentProfile.objects.select_related("user").get(id=parsed["student_id"])
        else:
            student = StudentProfile.objects.select_related("user").get(student_code=parsed["student_code"])

        with transaction.atomic():
            enrollment, created = StudentMonthlyEnrollment.objects.get_or_create(
                period=group.period,
                student=student,
                defaults={"group": group, "status": ser.validated_data.get("status", "active")},
            )
            if not created:
                enrollment.group = group
                enrollment.status = ser.validated_data.get("status", enrollment.status)
                enrollment.save()

        # Optionnel: sync StudentProfile quick fields
        student.current_level = group.level.label
        student.group_name = group.group_name
        student.save(update_fields=["current_level", "group_name"])

        return ok(
            data={
                "enrollment_id": enrollment.id,
                "student_id": student.id,
                "student_code": student.student_code,
                "group_id": group.id,
                "period": group.period.key,
                "status": enrollment.status,
                "qr_version": parsed["version"],
            },
            message="Student enrolled successfully",
        )


# ---------------------------
# 5) Homework CRUD + submissions view
# ---------------------------
class TeacherHomeworkViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated, IsTeacher]
    serializer_class = HomeworkSerializer
    queryset = Homework.objects.all()

    def get_queryset(self):
        teacher = self.request.user.teacher_profile
        qs = super().get_queryset().filter(teacher=teacher)

        group_id = self.request.query_params.get("group")
        course_id = self.request.query_params.get("course")
        period_key = self.request.query_params.get("period")

        if group_id:
            qs = qs.filter(group_id=group_id)
        if course_id:
            qs = qs.filter(course_id=course_id)
        if period_key:
            qs = qs.filter(period__key=period_key)

        return qs.order_by("-created_at")

    def perform_create(self, serializer):
        teacher = self.request.user.teacher_profile
        group = serializer.validated_data["group"]
        course = serializer.validated_data["course"]

        # security: teacher must be assigned to this class/course
        if not TeacherCourseAssignment.objects.filter(teacher=teacher, monthly_group=group, course=course).exists():
            raise ValueError("Not assigned to this course/class.")

        serializer.save(
            teacher=teacher,
            period=group.period
        )

    @action(detail=True, methods=["get"])
    def submissions(self, request, pk=None):
        """
        GET /api/teacher/homeworks/{id}/submissions/
        """
        teacher = request.user.teacher_profile
        hw = self.get_queryset().select_related("group", "course").get(id=pk)

        subs = HomeworkSubmission.objects.select_related("student__user").filter(homework=hw).order_by("-created_at")
        return ok(HomeworkSubmissionSerializer(subs, many=True).data)


class TeacherHomeworkSubmissionViewSet(ModelViewSet):
    """
    Teacher can grade/update submissions:
    PATCH /api/teacher/submissions/{id}/  (score, teacher_comment, status)
    """
    permission_classes = [IsAuthenticated, IsTeacher]
    serializer_class = HomeworkSubmissionSerializer
    queryset = HomeworkSubmission.objects.all()

    def get_queryset(self):
        teacher = self.request.user.teacher_profile
        # only submissions for teacher's homeworks
        return super().get_queryset().filter(homework__teacher=teacher).select_related("homework", "student__user")

# ---------------------------
# (Bonus) tu peux aussi faire des endpoints pour les remarques, objectifs mensuels, et les scans de justificatifs
# ---------------------------

class TeacherProofScanViewSet(ViewSet):
    permission_classes = [IsAuthenticated, IsTeacher]

    @action(detail=False, methods=["post"])
    def scan(self, request):
        teacher = request.user.teacher_profile

        group_id = request.data.get("group_id")
        qr_data = request.data.get("qr_data")
        purpose = request.data.get("purpose")
        course_id = request.data.get("course")
        note = request.data.get("note", "")
        meta = request.data.get("meta", {}) or {}

        if not group_id or not qr_data or not purpose:
            return bad("group_id, qr_data, purpose are required", status_code=status.HTTP_400_BAD_REQUEST)

        group = MonthlyClassGroup.objects.select_related("period").get(id=group_id)

        if not TeacherCourseAssignment.objects.filter(teacher=teacher, monthly_group=group).exists():
            return bad("Not allowed", status_code=status.HTTP_403_FORBIDDEN)

        try:
            parsed = parse_qr_data(qr_data)
        except ValueError as e:
            return bad(str(e), status_code=status.HTTP_400_BAD_REQUEST)

        if parsed.get("student_id"):
            student = StudentProfile.objects.select_related("user").get(id=parsed["student_id"])
        else:
            student = StudentProfile.objects.select_related("user").get(student_code=parsed["student_code"])

        with transaction.atomic():
            # ✅ save scan proof
            scan = StudentProofScan.objects.create(
                teacher=teacher,
                period=group.period,
                group=group,
                student=student,
                course_id=course_id if course_id else None,
                purpose=purpose,
                note=note,
                meta=meta,
            )

            # ✅ ensure enrollment exists for this period
            enrollment, _ = StudentMonthlyEnrollment.objects.get_or_create(
                period=group.period,
                student=student,
                defaults={"group": group, "status": "active"},
            )

            # ✅ keep group aligned
            if enrollment.group_id != group.id:
                enrollment.group = group

            # ✅ unlock exam when purpose is exam_eligible
            if purpose == "exam_eligible":
                enrollment.exam_unlock = True

            enrollment.save()

        return ok(
            {
                "scan": StudentProofScanSerializer(scan).data,
                "enrollment": StudentMonthlyEnrollmentSerializer(enrollment).data,
            },
            message="Proof scan saved",
        )

class TeacherStudentRemarkViewSet(ModelViewSet):
    """
    CRUD remarks:
    GET /api/teacher/student-remarks/?group=5&student=12&period=2026-02
    POST /api/teacher/student-remarks/
    """
    permission_classes = [IsAuthenticated, IsTeacher]
    serializer_class = StudentRemarkSerializer
    queryset = StudentRemark.objects.all()

    def get_queryset(self):
        teacher = self.request.user.teacher_profile
        qs = super().get_queryset().filter(teacher=teacher)

        group = self.request.query_params.get("group")
        student = self.request.query_params.get("student")
        period_key = self.request.query_params.get("period")

        if group:
            qs = qs.filter(group_id=group)
        if student:
            qs = qs.filter(student_id=student)
        if period_key:
            qs = qs.filter(period__key=period_key)

        return qs.order_by("-created_at")

    def perform_create(self, serializer):
        teacher = self.request.user.teacher_profile
        group = serializer.validated_data["group"]

        # sécurité: teacher doit enseigner dans ce group
        if not TeacherCourseAssignment.objects.filter(teacher=teacher, monthly_group=group).exists():
            raise ValueError("Not allowed")

        serializer.save(
            teacher=teacher,
            period=group.period,
        )


class TeacherMonthlyObjectiveViewSet(ModelViewSet):
    """
    CRUD objectives (titular recommended):
    GET /api/teacher/objectives/?group=5&period=2026-02
    POST /api/teacher/objectives/   (upsert possible)
    """
    permission_classes = [IsAuthenticated, IsTeacher]
    serializer_class = StudentMonthlyObjectiveSerializer
    queryset = StudentMonthlyObjective.objects.all()

    def get_queryset(self):
        teacher = self.request.user.teacher_profile
        qs = super().get_queryset().filter(teacher=teacher)

        group = self.request.query_params.get("group")
        student = self.request.query_params.get("student")
        period_key = self.request.query_params.get("period")

        if group:
            qs = qs.filter(group_id=group)
        if student:
            qs = qs.filter(student_id=student)
        if period_key:
            qs = qs.filter(period__key=period_key)

        return qs.order_by("-created_at")

    def perform_create(self, serializer):
        teacher = self.request.user.teacher_profile
        group = serializer.validated_data["group"]

        # ✅ option pro: seul le titulaire peut écrire les objectifs
        is_titular = TeacherCourseAssignment.objects.filter(
            teacher=teacher, monthly_group=group, is_titular=True
        ).exists()
        if not is_titular:
            raise ValueError("Only titular teacher can create monthly objectives.")

        # upsert (period, group, student) unique
        student = serializer.validated_data["student"]
        defaults = {
            "teacher": teacher,
            "objectives": serializer.validated_data.get("objectives", {}),
            "teacher_description": serializer.validated_data.get("teacher_description", ""),
        }

        obj, created = StudentMonthlyObjective.objects.update_or_create(
            period=group.period, group=group, student=student,
            defaults=defaults
        )
        # on renvoie l’objet créé/maj (DRF create)
        serializer.instance = obj


class TeacherClassGeneralRemarkViewSet(ModelViewSet):
    """
    Class remarks + solutions:
    GET /api/teacher/class-remarks/?group=5&period=2026-02
    POST /api/teacher/class-remarks/
    """
    permission_classes = [IsAuthenticated, IsTeacher]
    serializer_class = ClassGeneralRemarkSerializer
    queryset = ClassGeneralRemark.objects.all()

    def get_queryset(self):
        teacher = self.request.user.teacher_profile
        qs = super().get_queryset().filter(teacher=teacher)

        group = self.request.query_params.get("group")
        period_key = self.request.query_params.get("period")

        if group:
            qs = qs.filter(group_id=group)
        if period_key:
            qs = qs.filter(period__key=period_key)

        return qs.order_by("-created_at")

    def perform_create(self, serializer):
        teacher = self.request.user.teacher_profile
        group = serializer.validated_data["group"]

        if not TeacherCourseAssignment.objects.filter(teacher=teacher, monthly_group=group).exists():
            raise ValueError("Not allowed")

        serializer.save(
            teacher=teacher,
            period=group.period,
        )
