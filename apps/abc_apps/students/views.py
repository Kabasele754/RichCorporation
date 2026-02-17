from __future__ import annotations
from datetime import date
from rest_framework.viewsets import ViewSet
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q

from apps.abc_apps.academics.models import StudentMonthlyEnrollment, TeacherCourseAssignment
from apps.abc_apps.academics.serializers import (
    StudentMonthlyEnrollmentSerializer,
    TeacherCourseAssignmentSerializer,
)

from apps.abc_apps.app_teacher.models import WeeklyTeachingPlan, Homework, StudentRemark, StudentMonthlyObjective, StudentProofScan
from apps.abc_apps.app_teacher.serializers import (
    WeeklyTeachingPlanSerializer,
    HomeworkSerializer,
    StudentRemarkSerializer,
    StudentMonthlyObjectiveSerializer,
    StudentProofScanSerializer,
)
from apps.common.permissions import IsStudent
from apps.common.responses import bad, ok


class StudentDashboardViewSet(ViewSet):
    permission_classes = [IsAuthenticated, IsStudent]

    def list(self, request):
        """
        GET /api/student/dashboard/?period=2026-02
        """
        student = request.user.student_profile
        period_key = request.query_params.get("period")

        qs = StudentMonthlyEnrollment.objects.select_related(
            "period", "group__room", "group__level"
        ).filter(student=student)

        if period_key:
            qs = qs.filter(period__key=period_key)

        qs = qs.order_by("-period__year", "-period__month")
        current = qs.first()

        if not current:
            return ok({"enrollment": None}, message="No enrollment")

        # teacher assignments for that group/period
        assignments = TeacherCourseAssignment.objects.select_related(
            "teacher__user", "course", "classroom", "period", "monthly_group"
        ).filter(monthly_group=current.group, period=current.period)

        return ok({
            "enrollment": StudentMonthlyEnrollmentSerializer(current).data,
            "assignments": TeacherCourseAssignmentSerializer(assignments, many=True).data,
        }, message="Student dashboard")


class StudentWeeklyPlanViewSet(ViewSet):
    permission_classes = [IsAuthenticated, IsStudent]

    def list(self, request):
        """
        GET /api/student/weekly-plans/?week_start=YYYY-MM-DD&course=<id>
        """
        student = request.user.student_profile
        week_start = request.query_params.get("week_start")
        course_id = request.query_params.get("course")

        current = StudentMonthlyEnrollment.objects.select_related("group", "period").filter(
            student=student
        ).order_by("-period__year", "-period__month").first()

        if not current:
            return bad("No enrollment found", status_code=403)

        qs = WeeklyTeachingPlan.objects.filter(
            monthly_group=current.group,
            period=current.period,
        ).select_related("course", "teacher__user")

        if week_start:
            qs = qs.filter(week_start=week_start)
        if course_id:
            qs = qs.filter(course_id=course_id)

        qs = qs.order_by("-week_start", "course__name")

        return ok({"items": WeeklyTeachingPlanSerializer(qs, many=True).data}, message="Weekly plans")


class StudentHomeworkViewSet(ViewSet):
    permission_classes = [IsAuthenticated, IsStudent]

    def list(self, request):
        student = request.user.student_profile
        course_id = request.query_params.get("course")
        teacher_id = request.query_params.get("teacher")  # ✅ NEW

        current = StudentMonthlyEnrollment.objects.select_related("group", "period") \
            .filter(student=student) \
            .order_by("-period__year", "-period__month") \
            .first()

        if not current:
            return bad("No enrollment", status_code=403)

        qs = Homework.objects.filter(
            group=current.group,
            period=current.period,
        ).select_related("course", "teacher__user").order_by("-created_at")

        if course_id:
            qs = qs.filter(course_id=course_id)

        if teacher_id:
            qs = qs.filter(teacher_id=teacher_id)  # ✅ NEW

        return ok({"items": HomeworkSerializer(qs, many=True).data}, message="Homeworks")

class StudentObjectivesViewSet(ViewSet):
    permission_classes = [IsAuthenticated, IsStudent]

    def list(self, request):
        student = request.user.student_profile
        current = StudentMonthlyEnrollment.objects.select_related("group", "period").filter(
            student=student
        ).order_by("-period__year", "-period__month").first()
        if not current:
            return bad("No enrollment", status_code=403)

        qs = StudentMonthlyObjective.objects.filter(
            student=student,
            group=current.group,
            period=current.period,
        ).order_by("-created_at")

        return ok({"items": StudentMonthlyObjectiveSerializer(qs, many=True).data}, message="Objectives")


class StudentRemarksViewSet(ViewSet):
    permission_classes = [IsAuthenticated, IsStudent]

    def list(self, request):
        """
        GET /api/student/remarks/?period=2026-02&course=ID&teacher=ID&q=keyword&limit=100
        """
        student = request.user.student_profile

        # ✅ optional filters
        period_key = request.query_params.get("period")     # "2026-02" (si tu utilises code)
        course_id = request.query_params.get("course")      # int
        teacher_id = request.query_params.get("teacher")    # int
        q = (request.query_params.get("q") or "").strip()
        limit = int(request.query_params.get("limit", 100))

        # ✅ récupérer enrollment courant (ou selon period)
        enroll_qs = StudentMonthlyEnrollment.objects.select_related(
            "group", "period"
        ).filter(student=student)

        if period_key:
            # ⚠️ selon ton modèle AcademicPeriod:
            # - si tu utilises "code" => period__code=period_key
            # - si tu utilises "key"  => period__key=period_key
            enroll_qs = enroll_qs.filter(period__code=period_key)

        current = enroll_qs.order_by("-period__year", "-period__month").first()

        if not current:
            return bad("No enrollment", status_code=403)

        qs = StudentRemark.objects.filter(
            student=student,
            group=current.group,
            period=current.period,
        )

        # ✅ server filters
        if course_id:
            qs = qs.filter(course_id=course_id)

        if teacher_id:
            qs = qs.filter(teacher_id=teacher_id)

        if q:
            # recherche sur title + remark (adapte si tes champs s'appellent autrement)
            qs = qs.filter(
                Q(title__icontains=q) | Q(remark__icontains=q)
            )

        qs = qs.select_related("course", "teacher__user").order_by("-created_at")[:limit]

        return ok(
            {"items": StudentRemarkSerializer(qs, many=True).data},
            message="Remarks",
        )

class StudentProofScansViewSet(ViewSet):
    permission_classes = [IsAuthenticated, IsStudent]

    def list(self, request):
        student = request.user.student_profile
        current = StudentMonthlyEnrollment.objects.select_related("group", "period").filter(
            student=student
        ).order_by("-period__year", "-period__month").first()
        if not current:
            return bad("No enrollment", status_code=403)

        qs = StudentProofScan.objects.filter(
            student=student,
            group=current.group,
            period=current.period,
        ).select_related("course").order_by("-scanned_at")

        return ok({"items": StudentProofScanSerializer(qs, many=True).data}, message="Proof scans")
