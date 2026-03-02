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
    get_teacher_speech_groups,
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
            teacher=teacher, period=period,
             is_speech_teacher=True, 
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

def _is_admin(user):
    return getattr(user, "role", "") in ["principal", "admin", "staff", "superadmin"]

def _teacher_can_access_speech(teacher_profile, speech: Speech):
    group_ids, period = get_teacher_active_groups(teacher_profile)
    is_own = (speech.author_type == "teacher" and speech.teacher_id == teacher_profile.id)
    is_student_in_my_class = (
        speech.author_type == "student"
        and speech.period_id == period.id
        and speech.group_id in group_ids
    )
    return is_own or is_student_in_my_class

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
        # print("Base QS:", qs.query)

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
        LIST endpoints restent filtrés par rôle (my list).
        MAIS les actions detail (retrieve/like/comment/upload-audio/add-revision/coach/delete/patch/...)
        doivent voir tous les speeches sinon get_object() retourne 404.
        """
        qs = self._base_qs()
        u = self.request.user

        # ✅ IMPORTANT: actions detail doivent accéder au speech cible
        detail_actions = {
            # DRF default detail actions
            "retrieve",
            "update", "partial_update",
            "destroy",

            # social
            "like", "comment", "comments",

            # workflow
            "submit", "request_publish", "decide",

            # teacher tools
            "upload_audio",
            "add_revision", "delete_revision",
            "coach", "delete_coaching",
            "delete_audio",
        }

        if getattr(self, "action", None) in detail_actions:
            return qs.order_by("-created_at")

        # ✅ LIST "my speeches" (inchangé)
        if getattr(u, "role", "") == "student":
            return qs.filter(student__user=u).order_by("-created_at")

        if getattr(u, "role", "") == "teacher":
            return qs.filter(teacher__user=u).order_by("-created_at")

        return qs.order_by("-created_at")

    def perform_create(self, serializer):
        u = self.request.user

        # ✅ STUDENT: period/group/room from active enrollment (inchangé)
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
                month=period.code,
                status="draft",
            )
            return

        # ✅ TEACHER: group from TITULAR assignment (AUTO)
        if getattr(u, "role", "") == "teacher":
            teacher = u.teacher_profile
            today = timezone.localdate()
            period = get_or_create_period_from_date(today)

            # 🔥 récupérer le groupe titulaire du teacher pour ce period
            titular_qs = (
                TeacherCourseAssignment.objects
                .select_related("monthly_group__room")
                .filter(
                    teacher=teacher,
                    period=period,
                    is_titular=True,
                )
                .exclude(monthly_group__isnull=True)
            )

            count = titular_qs.count()
            if count == 0:
                raise ValidationError({
                    "detail": "You have no titular class for the current period. Cannot create a class speech."
                })
            if count > 1:
                raise ValidationError({
                    "detail": "Multiple titular classes found. Please contact admin to keep only one titular assignment."
                })

            assign = titular_qs.first()
            group = assign.monthly_group
            room = group.room

            serializer.save(
                author_type="teacher",
                teacher=teacher,
                period=period,
                group=group,
                room=room,
                month=period.code,
                status="draft",
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
        group_ids, period = get_teacher_speech_groups(teacher)   # ✅ ici

        qs = (self._base_qs()
            .filter(period=period, group_id__in=group_ids)
            .filter(author_type="student")
            .filter(status__in=["draft","corrected","coached","submitted", "needs_revision", "pending_approval", "published"])
            .order_by("-submitted_at", "-created_at")[:80])
        

        ser = SpeechSerializer(qs, many=True, context={"request": request})
        return ok({"items": ser.data}, "Teacher inbox (Speech Teacher) ✅")
    
    # ──────────────────────────────
    # ✅ TEACHER MY (speeches of his classes)    
    # ──────────────────────────────
    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated, IsTeacher], url_path="teacher/my")
    def teacher_my(self, request):
        teacher = request.user.teacher_profile
        qs = (self._base_qs()
            .filter(author_type="teacher", teacher=teacher, is_deleted=False)
            .order_by("-created_at")[:120])
        ser = SpeechSerializer(qs, many=True, context={"request": request})
        return ok({"items": ser.data}, "Teacher my speeches ✅")    

    # ─────────────────────────────
    # Social actions (auth only)
    # ─────────────────────────────
    # ─────────────────────────────
    # Workflow endpoints
    # ─────────────────────────────

    @action(detail=True, methods=["post"], url_path="submit")
    def submit(self, request, pk=None):
        speech = self.get_object()

        if request.user.role == "student" and (not speech.student_id or speech.student.user_id != request.user.id):
            return bad("Not allowed", 403)
        if request.user.role == "teacher" and (not speech.teacher_id or speech.teacher.user_id != request.user.id):
            return bad("Not allowed", 403)

        if speech.status not in ["draft", "needs_revision"]:
            return bad("Cannot submit in current status", 400)

        speech.status = "submitted"
        speech.submitted_at = timezone.now()
        speech.save(update_fields=["status", "submitted_at"])
        return ok({"speech": SpeechSerializer(speech, context={"request": request}).data}, "Submitted ✅")

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsTeacher], url_path="add-revision")
    def add_revision(self, request, pk=None):
        speech = self.get_object()
        revised_content = (request.data.get("revised_content") or "").strip()
        notes = (request.data.get("notes") or "").strip()
        is_final = bool(request.data.get("is_final", False))

        if not revised_content:
            return bad("revised_content is required", 400)

        last = SpeechRevision.objects.filter(speech=speech).order_by("-version").first()
        next_version = (last.version + 1) if last else 1

        with transaction.atomic():
            rev = SpeechRevision.objects.create(
                speech=speech,
                version=next_version,
                revised_by=request.user,
                revised_content=revised_content,
                notes=notes,
                is_final=is_final,
            )
            speech.status = "corrected"
            speech.save(update_fields=["status"])

        return ok({"revision": SpeechRevisionSerializer(rev).data}, "Correction saved ✅")
    
    @action(
    detail=True,
    methods=["delete"],
    permission_classes=[IsAuthenticated, IsTeacher],
    url_path=r"revisions/(?P<revision_id>[^/.]+)")
    def delete_revision(self, request, pk=None, revision_id=None):
        speech = self.get_object()
        teacher = request.user.teacher_profile

        # ✅ teacher must access this speech
        if not _is_admin(request.user) and not _teacher_can_access_speech(teacher, speech):
            return bad("Not allowed (not your class)", 403)

        try:
            rev = SpeechRevision.objects.get(id=int(revision_id), speech=speech)
        except Exception:
            return bad("Revision not found", 404)

        # ✅ only owner or admin
        if not _is_admin(request.user) and rev.revised_by_id != request.user.id:
            return bad("Not allowed", 403)

        rev.delete()

        # (optionnel) status recalcul
        if not speech.revisions.exists() and speech.status == "corrected":
            speech.status = "submitted" if speech.submitted_at else "draft"
            speech.save(update_fields=["status"])

        return ok({"deleted": True, "revision_id": int(revision_id)}, "Revision deleted ✅")
    
    @action(
    detail=True,
    methods=["patch"],
    permission_classes=[IsAuthenticated, IsTeacher],
    url_path=r"revisions/(?P<revision_id>[^/.]+)/update"
)
    def update_revision(self, request, pk=None, revision_id=None):
        speech = self.get_object()
        teacher = request.user.teacher_profile

        if not _is_admin(request.user) and not _teacher_can_access_speech(teacher, speech):
            return bad("Not allowed (not your class)", 403)

        try:
            rev = SpeechRevision.objects.get(id=int(revision_id), speech=speech)
        except Exception:
            return bad("Revision not found", 404)

        if not _is_admin(request.user) and rev.revised_by_id != request.user.id:
            return bad("Not allowed", 403)

        revised_content = request.data.get("revised_content", None)
        notes = request.data.get("notes", None)
        is_final = request.data.get("is_final", None)

        if revised_content is not None:
            rev.revised_content = str(revised_content).strip()
        if notes is not None:
            rev.notes = str(notes).strip()
        if is_final is not None:
            rev.is_final = bool(is_final)

        rev.save()
        return ok({"revision": SpeechRevisionSerializer(rev).data}, "Revision updated ✅")
    
    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsTeacher], url_path="coach")
    def coach(self, request, pk=None):
        speech = self.get_object()
        notes = (request.data.get("pronunciation_notes") or "").strip()
        word_tips = request.data.get("word_tips", [])
        is_final = bool(request.data.get("is_final", False))

        with transaction.atomic():
            c = SpeechCoaching.objects.create(
                speech=speech,
                teacher=request.user.teacher_profile,
                pronunciation_notes=notes,
                word_tips=word_tips if isinstance(word_tips, list) else [],
                is_final=is_final,
            )
            speech.status = "coached"
            speech.save(update_fields=["status"])

        return ok({"coaching": SpeechCoachingSerializer(c).data}, "Coaching saved ✅")
    
    @action(
    detail=True,
    methods=["delete"],
    permission_classes=[IsAuthenticated, IsTeacher],
    url_path=r"coachings/(?P<coaching_id>[^/.]+)"
)
    def delete_coaching(self, request, pk=None, coaching_id=None):
        speech = self.get_object()
        teacher = request.user.teacher_profile

        if not _is_admin(request.user) and not _teacher_can_access_speech(teacher, speech):
            return bad("Not allowed (not your class)", 403)

        try:
            c = SpeechCoaching.objects.get(id=int(coaching_id), speech=speech)
        except Exception:
            return bad("Coaching not found", 404)

        # ✅ only owner or admin
        # c.teacher est TeacherProfile -> compare c.teacher.user_id
        if not _is_admin(request.user) and getattr(c.teacher, "user_id", None) != request.user.id:
            return bad("Not allowed", 403)

        c.delete()

        # (optionnel) status recalcul
        if not speech.coachings.exists() and speech.status == "coached":
            if speech.revisions.exists():
                speech.status = "corrected"
            else:
                speech.status = "submitted" if speech.submitted_at else "draft"
            speech.save(update_fields=["status"])

        return ok({"deleted": True, "coaching_id": int(coaching_id)}, "Coaching deleted ✅")
    
    @action(
    detail=True,
    methods=["patch"],
    permission_classes=[IsAuthenticated, IsTeacher],
    url_path=r"coachings/(?P<coaching_id>[^/.]+)/update"
    )
    def update_coaching(self, request, pk=None, coaching_id=None):
        speech = self.get_object()
        teacher = request.user.teacher_profile

        if not _is_admin(request.user) and not _teacher_can_access_speech(teacher, speech):
            return bad("Not allowed (not your class)", 403)

        try:
            c = SpeechCoaching.objects.get(id=int(coaching_id), speech=speech)
        except Exception:
            return bad("Coaching not found", 404)

        if not _is_admin(request.user) and getattr(c.teacher, "user_id", None) != request.user.id:
            return bad("Not allowed", 403)

        notes = request.data.get("pronunciation_notes", None)
        word_tips = request.data.get("word_tips", None)
        is_final = request.data.get("is_final", None)

        if notes is not None:
            c.pronunciation_notes = str(notes).strip()
        if word_tips is not None:
            c.word_tips = word_tips if isinstance(word_tips, list) else []
        if is_final is not None:
            c.is_final = bool(is_final)

        c.save()
        return ok({"coaching": SpeechCoachingSerializer(c).data}, "Coaching updated ✅")

    @action(detail=True, methods=["post"], url_path="upload-audio")
    def upload_audio(self, request, pk=None):
        speech = self.get_object()
        kind = (request.data.get("kind") or "").strip()
        f = request.FILES.get("audio_file")

        if kind not in ["student_recording", "teacher_coaching", "tts"]:
            return bad("Invalid kind", 400)
        if not f:
            return bad("audio_file is required", 400)

        if kind == "student_recording" and request.user.role != "student":
            return bad("Only students can upload student recordings", 403)
        if kind == "teacher_coaching" and request.user.role != "teacher":
            return bad("Only teachers can upload coaching audio", 403)

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
    
    @action(
    detail=True,
    methods=["delete"],
    permission_classes=[IsAuthenticated],
    url_path=r"audios/(?P<audio_id>[^/.]+)"
)
    def delete_audio(self, request, pk=None, audio_id=None):
        speech = self.get_object()

        # ✅ teacher can only delete audios on speech he can access
        if request.user.role == "teacher" and not _is_admin(request.user):
            if not _teacher_can_access_speech(request.user.teacher_profile, speech):
                return bad("Not allowed (not your class)", 403)

        try:
            audio = SpeechAudio.objects.get(id=int(audio_id), speech=speech)
        except Exception:
            return bad("Audio not found", 404)

        # ✅ owner or admin
        if not _is_admin(request.user) and audio.uploaded_by_id != request.user.id:
            return bad("Not allowed", 403)

        # delete file + db
        if audio.audio_file:
            audio.audio_file.delete(save=False)
        audio.delete()

        return ok({"deleted": True, "audio_id": int(audio_id)}, "Audio deleted ✅")
    @action(detail=True, methods=["post"], url_path="request-publish")
    def request_publish(self, request, pk=None):
        speech = self.get_object()

        if request.user.role == "student" and (not speech.student_id or speech.student.user_id != request.user.id):
            return bad("Not allowed", 403)
        if request.user.role == "teacher" and (not speech.teacher_id or speech.teacher.user_id != request.user.id):
            return bad("Not allowed", 403)

        if not speech.cover_image:
            return bad("Cover image is required to publish.", 400)

        has_final_rev = speech.revisions.filter(is_final=True).exists()
        has_final_coach = speech.coachings.filter(is_final=True).exists()

        if speech.author_type == "student":
            if not has_final_rev:
                return bad("Teacher final correction is required before publish.", 400)
            if not has_final_coach:
                return bad("Teacher final coaching is required before publish.", 400)

        speech.status = "pending_approval"
        speech.save(update_fields=["status"])
        return ok({"speech": SpeechSerializer(speech, context={"request": request}).data}, "Sent for approval ✅")

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsPrincipal], url_path="decide")
    def decide(self, request, pk=None):
        speech = self.get_object()
        decision = (request.data.get("decision") or "").strip()
        reason = (request.data.get("reason") or "").strip()

        if decision not in ["approve", "reject"]:
            return bad("decision must be approve/reject", 400)
        if speech.status != "pending_approval":
            return bad("Speech is not pending approval", 400)

        with transaction.atomic():
            SpeechApproval.objects.update_or_create(
                speech=speech,
                defaults={
                    "decided_by": request.user,
                    "decision": decision,
                    "reason": reason,
                    "decided_at": timezone.now(),
                },
            )

            if decision == "approve":
                speech.status = "published"
                speech.published_at = timezone.now()

                vis = (request.data.get("visibility") or "").strip()
                if vis in ["private", "class", "school", "public"]:
                    speech.visibility = vis

                speech.save(update_fields=["status", "published_at", "visibility"])
                msg = "Approved & Published ✅"
            else:
                speech.status = "rejected"
                speech.save(update_fields=["status"])
                msg = "Rejected ❌"

        return ok({"speech": SpeechSerializer(speech, context={"request": request}).data}, msg)

    # ─────────────────────────────
    # Social actions
    # ─────────────────────────────
    @action(detail=True, methods=["post"], url_path="like")
    def like(self, request, pk=None):
        speech = self.get_object()
        if speech.status != "published":
            return bad("Not published", 400)

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

        content = (request.data.get("content") or "").strip()
        if not content:
            print("Content is empty")
            return bad("content is required", 400)

        c = SpeechComment.objects.create(speech=speech, user=request.user, content=content)
        return ok({"comment": {"id": c.id, "content": c.content}}, "Comment added ✅")
    
    @action(detail=True, methods=["get"], url_path="comments")
    def comments(self, request, pk=None):
        speech = self.get_object()

        # ✅ seulement published si tu veux
        if speech.status != "published":
            print("Speech not published, cannot show comments")
            return ok({"items": []}, "Not published")

        qs = (SpeechComment.objects
              .filter(speech=speech, is_hidden=False)
              .select_related("user")
              .order_by("-created_at")[:200])

        ser = SpeechCommentSerializer(qs, many=True)
        return ok({"items": ser.data}, "Comments")
  
    
    
    
    