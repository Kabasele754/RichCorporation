# apps/abc_apps/speeches/viewsets.py
from django.db import transaction
from django.db.models import Count, Exists, OuterRef, Value, BooleanField, Q
from django.utils import timezone

from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.exceptions import ValidationError

from apps.abc_apps.accounts.permissions import IsTeacher, IsPrincipal
from apps.abc_apps.academics.utils import (
    get_active_enrollment_for_student,
    get_teacher_active_groups,
    get_or_create_period_from_date,
)
from apps.abc_apps.academics.models import MonthlyClassGroup, StudentMonthlyEnrollment, TeacherCourseAssignment

from apps.abc_apps.speeches.models import (
    Speech, SpeechRevision, SpeechCoaching, SpeechAudio,
    SpeechApproval, SpeechLike, SpeechComment
)
from apps.abc_apps.speeches.serializers import (
    SpeechSerializer, SpeechRevisionSerializer, SpeechCoachingSerializer,
    SpeechAudioSerializer, SpeechCommentSerializer
)
from apps.common.responses import ok, bad


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────
def _norm(x):
    if not x:
        return None
    x = str(x).strip()
    return x or None

def _norm_lower(x):
    x = _norm(x)
    return x.lower() if x else None

def _parse_month_code(month_code: str):
    """
    "2026-02" -> (2026, 2)
    """
    mc = _norm(month_code)
    if not mc:
        return (None, None)
    try:
        y_str, m_str = mc.split("-", 1)
        y = int(y_str)
        m = int(m_str)
        if m < 1 or m > 12:
            return (None, None)
        return (y, m)
    except Exception:
        return (None, None)

def _apply_filters(qs, request):
    qp = request.query_params
    month = _norm(qp.get("month"))              # "2026-02"
    category = _norm_lower(qp.get("category"))  # "info"...
    author = _norm_lower(qp.get("author"))      # "student"|"teacher"|"all"
    level_id = qp.get("level_id")
    group_id = qp.get("group_id")

    if month:
        y, m = _parse_month_code(month)
        if y and m:
            qs = qs.filter(period__year=y, period__month=m)

    if category and category != "all":
        qs = qs.filter(category=category)

    if author and author != "all":
        qs = qs.filter(author_type=author)

    if level_id:
        try:
            qs = qs.filter(group__level_id=int(level_id))
        except Exception:
            pass

    if group_id:
        try:
            qs = qs.filter(group_id=int(group_id))
        except Exception:
            pass

    return qs


def _class_visibility_predicate(user):
    """
    ✅ visibility="class" STRICT:
    - student: must have active enrollment for that (period, group)
    - teacher: must have course assignment for that (period, monthly_group)
    - principal/staff: allow
    """
    if not (user and user.is_authenticated):
        return Q(pk__in=[])  # none

    role = getattr(user, "role", "")
    if role in ["principal", "admin", "staff", "superadmin"]:
        return Q()  # allow all class speeches

    today = timezone.localdate()
    period = get_or_create_period_from_date(today)

    if role == "student":
        student = getattr(user, "student_profile", None)
        if not student:
            return Q(pk__in=[])
        allowed_groups = StudentMonthlyEnrollment.objects.filter(
            student=student, period=period, status="active"
        ).values_list("group_id", flat=True)
        return Q(period=period, group_id__in=allowed_groups)

    if role == "teacher":
        teacher = getattr(user, "teacher_profile", None)
        if not teacher:
            return Q(pk__in=[])
        allowed_groups = TeacherCourseAssignment.objects.filter(
            teacher=teacher, period=period
        ).values_list("monthly_group_id", flat=True)
        return Q(period=period, group_id__in=allowed_groups)

    return Q(pk__in=[])


def _apply_visibility_for_feed(qs, request):
    """
    Public endpoints => uniquement published + pas deleted
    Anonymous => public only
    Auth => public + school + class(strict)
    """
    u = getattr(request, "user", None)
    qs = qs.filter(status="published", is_deleted=False)

    if not (u and u.is_authenticated):
        return qs.filter(visibility="public")

    # public + school always
    base = Q(visibility__in=["public", "school"])

    # class strict
    class_q = Q(visibility="class") & _class_visibility_predicate(u)

    return qs.filter(base | class_q)


# ─────────────────────────────────────────────
# ViewSet
# ─────────────────────────────────────────────
class SpeechViewSet(ModelViewSet):
    serializer_class = SpeechSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        # public endpoints: lecture seulement
        if self.action in ["feed", "month", "last_month", "popular", "latest", "comments"]:
            return [AllowAny()]

        # social actions require login (sinon request.user = AnonymousUser)
        if self.action in ["like", "comment", "upload_audio"]:
            return [IsAuthenticated()]

        return super().get_permissions()

    def _base_qs(self):
        u = getattr(self.request, "user", None)

        qs = (
            Speech.objects
            .select_related("period", "group", "group__level", "room", "student__user", "teacher__user")
            .filter(is_deleted=False)
        )
        print("Base QS:", qs.query)

        if u and u.is_authenticated:
            qs = qs.annotate(
                likes_count=Count("likes", distinct=True),
                comments_count=Count("comments", distinct=True),
                liked_by_me=Exists(SpeechLike.objects.filter(speech_id=OuterRef("pk"), user=u)),
            )
        else:
            qs = qs.annotate(
                likes_count=Count("likes", distinct=True),
                comments_count=Count("comments", distinct=True),
                liked_by_me=Value(False, output_field=BooleanField()),
            )

        return qs

    def get_queryset(self):
        """
        Authenticated "my list":
        - student => only his speeches
        - teacher => only his speeches
        - staff => all
        """
        u = self.request.user
        qs = self._base_qs()

        if getattr(u, "role", "") == "student":
            return qs.filter(student__user=u).order_by("-created_at")

        if getattr(u, "role", "") == "teacher":
            return qs.filter(teacher__user=u).order_by("-created_at")

        return qs.order_by("-created_at")

    def perform_create(self, serializer):
        u = self.request.user

        # ✅ STUDENT: period/group/room from active enrollment
        if getattr(u, "role", "") == "student":
            student = u.student_profile
            enroll, period = get_active_enrollment_for_student(student)
            if not enroll:
                raise ValidationError({"detail": "Student is not enrolled for the current month."})

            group = enroll.group
            room = group.room

            serializer.save(
                author_type="student",
                student=student,
                period=period,
                group=group,
                room=room,
                month=period.code,       # ✅ "YYYY-MM"
                status="draft",          # ✅ draft
                # category comes from request if provided; else default model "info"
            )
            return

        # ✅ TEACHER: must choose group (class speech)
        if getattr(u, "role", "") == "teacher":
            teacher = u.teacher_profile
            group_ids, period = get_teacher_active_groups(teacher)

            raw_group_id = self.request.data.get("group")
            if not raw_group_id:
                raise ValidationError({"group": "group is required for teacher speech."})

            try:
                group_id = int(raw_group_id)
            except Exception:
                raise ValidationError({"group": "invalid group id"})

            if group_id not in group_ids:
                raise ValidationError({"group": "You are not assigned to this group for current period."})

            group = MonthlyClassGroup.objects.select_related("room").get(id=group_id)
            room = group.room

            serializer.save(
                author_type="teacher",
                teacher=teacher,
                period=period,
                group=group,
                room=room,
                month=period.code,
                status="draft",   # ✅ draft like student
            )
            return

        serializer.save(status="draft")

    # ─────────────────────────────
    # Public/Home endpoints
    # ─────────────────────────────
    @action(detail=False, methods=["get"], url_path="feed")
    def feed(self, request):
        qs = _apply_visibility_for_feed(self._base_qs(), request)
        qs = _apply_filters(qs, request)
        qs = qs.order_by("-published_at", "-created_at")[:50]
        ser = SpeechSerializer(qs, many=True, context={"request": request})
        return ok({"items": ser.data}, "Feed")

    @action(detail=False, methods=["get"], url_path="month")
    def month(self, request):
        qs = _apply_visibility_for_feed(self._base_qs(), request)

        month_code = _norm(request.query_params.get("month"))
        if not month_code:
            today = timezone.localdate()
            month_code = f"{today.year:04d}-{today.month:02d}"

        y, m = _parse_month_code(month_code)
        if y and m:
            qs = qs.filter(period__year=y, period__month=m)

        qs = _apply_filters(qs, request).order_by("-published_at", "-created_at")[:50]
        ser = SpeechSerializer(qs, many=True, context={"request": request})
        return ok({"month": month_code, "items": ser.data}, "Month")

    @action(detail=False, methods=["get"], url_path="last-month")
    def last_month(self, request):
        qs = _apply_visibility_for_feed(self._base_qs(), request)

        today = timezone.localdate()
        y, m = today.year, today.month - 1
        if m == 0:
            y -= 1
            m = 12

        last_code = f"{y:04d}-{m:02d}"
        qs = qs.filter(period__year=y, period__month=m)
        qs = _apply_filters(qs, request).order_by("-published_at", "-created_at")[:50]
        ser = SpeechSerializer(qs, many=True, context={"request": request})
        return ok({"month": last_code, "items": ser.data}, "Last month")

    @action(detail=False, methods=["get"], url_path="popular")
    def popular(self, request):
        qs = _apply_visibility_for_feed(self._base_qs(), request)
        qs = _apply_filters(qs, request)
        qs = qs.order_by("-likes_count", "-comments_count", "-published_at", "-created_at")[:30]
        ser = SpeechSerializer(qs, many=True, context={"request": request})
        return ok({"items": ser.data}, "Popular")

    @action(detail=False, methods=["get"], url_path="latest")
    def latest(self, request):
        qs = _apply_visibility_for_feed(self._base_qs(), request)
        qs = _apply_filters(qs, request)
        qs = qs.order_by("-published_at", "-created_at")[:50]
        ser = SpeechSerializer(qs, many=True, context={"request": request})
        return ok({"items": ser.data}, "Latest")

    # ─────────────────────────────
    # ✅ TEACHER INBOX (speeches of his students / his classes)
    # ─────────────────────────────
    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated, IsTeacher], url_path="teacher/inbox")
    def teacher_inbox(self, request):
        teacher = request.user.teacher_profile
        group_ids, period = get_teacher_active_groups(teacher)

        qs = (self._base_qs()
              .filter(period=period, group_id__in=group_ids)
              .filter(author_type="student")
              .filter(status__in=["submitted", "needs_revision", "pending_approval", "published"])
              .order_by("-submitted_at", "-created_at")[:80])

        ser = SpeechSerializer(qs, many=True, context={"request": request})
        return ok({"items": ser.data}, "Teacher inbox")

    # ─────────────────────────────
    # Social actions (auth only)
    # ─────────────────────────────
    @action(detail=True, methods=["post"], url_path="like")
    def like(self, request, pk=None):
        speech = self.get_object()
        if speech.status != "published":
            return bad("Not published", 400)

        # ✅ if visibility class, ensure allowed
        if speech.visibility == "class":
            if not _class_visibility_predicate(request.user).resolve_expression:
                # (simple fallback) do explicit check:
                allowed = Speech.objects.filter(pk=speech.pk).filter(_class_visibility_predicate(request.user)).exists()
                if not allowed:
                    return bad("Not allowed", 403)

        obj, created = SpeechLike.objects.get_or_create(speech=speech, user=request.user)
        if not created:
            obj.delete()
            return ok({"liked": False}, "Unliked")
        return ok({"liked": True}, "Liked")

    @action(detail=True, methods=["post"], url_path="comment")
    def comment(self, request, pk=None):
        speech = self.get_object()
        if speech.status != "published":
            return bad("Not published", 400)

        if speech.visibility == "class":
            allowed = Speech.objects.filter(pk=speech.pk).filter(_class_visibility_predicate(request.user)).exists()
            if not allowed:
                return bad("Not allowed", 403)

        content = (request.data.get("content") or "").strip()
        if not content:
            return bad("content is required", 400)

        c = SpeechComment.objects.create(speech=speech, user=request.user, content=content)
        return ok({"comment": {"id": c.id, "content": c.content}}, "Comment added ✅")

    @action(detail=True, methods=["get"], url_path="comments")
    def comments(self, request, pk=None):
        speech = self.get_object()
        if speech.status != "published":
            return ok({"items": []}, "Not published")

        # ✅ if class speech: anonymous can't see; auth must be allowed
        if speech.visibility == "class":
            u = getattr(request, "user", None)
            if not (u and u.is_authenticated):
                return ok({"items": []}, "Private")
            allowed = Speech.objects.filter(pk=speech.pk).filter(_class_visibility_predicate(u)).exists()
            if not allowed:
                return ok({"items": []}, "Not allowed")

        qs = (SpeechComment.objects
              .filter(speech=speech, is_hidden=False)
              .select_related("user")
              .order_by("-created_at")[:200])

        ser = SpeechCommentSerializer(qs, many=True)
        return ok({"items": ser.data}, "Comments")

    # ─────────────────────────────
    # Audio upload (auth only)
    # ─────────────────────────────
    @action(detail=True, methods=["post"], url_path="upload-audio")
    def upload_audio(self, request, pk=None):
        speech = self.get_object()
        kind = (request.data.get("kind") or "").strip()
        f = request.FILES.get("audio_file")

        if kind not in ["student_recording", "teacher_coaching", "tts"]:
            return bad("Invalid kind", 400)
        if not f:
            return bad("audio_file is required", 400)

        # role checks
        if kind == "student_recording" and request.user.role != "student":
            return bad("Only students can upload student recordings", 403)

        if kind == "teacher_coaching" and request.user.role != "teacher":
            return bad("Only teachers can upload coaching audio", 403)

        # ✅ teacher coaching only for his classes or his own speech
        if request.user.role == "teacher" and kind == "teacher_coaching":
            teacher = request.user.teacher_profile
            group_ids, period = get_teacher_active_groups(teacher)

            # own speech OR student speech in his class
            is_own = (speech.author_type == "teacher" and speech.teacher_id == teacher.id)
            is_student_in_my_class = (
                speech.author_type == "student"
                and speech.period_id == period.id
                and speech.group_id in group_ids
            )

            if not (is_own or is_student_in_my_class):
                return bad("Not allowed (not your class)", 403)

        a = SpeechAudio.objects.create(
            speech=speech,
            kind=kind,
            uploaded_by=request.user,
            audio_file=f,
            duration_sec=request.data.get("duration_sec") or None,
            engine=(request.data.get("engine") or "").strip(),
            voice_name=(request.data.get("voice_name") or "").strip(),
            is_primary=bool(request.data.get("is_primary", False)),
        )

        return ok({"audio": SpeechAudioSerializer(a, context={"request": request}).data}, "Audio uploaded ✅")