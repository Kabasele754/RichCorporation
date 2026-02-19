from django.db import transaction
from django.db.models import Count, Exists, OuterRef
from django.utils import timezone

from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from apps.abc_apps.speeches.models import (
    Speech, SpeechRevision, SpeechCoaching, SpeechAudio, SpeechApproval,
    SpeechLike, SpeechComment, SpeechShare, SpeechVisibilityGrant
)
from apps.abc_apps.speeches.serializers import (
    SpeechSerializer, SpeechRevisionSerializer, SpeechCoachingSerializer, SpeechAudioSerializer
)
from apps.abc_apps.speeches.utils import get_active_enrollment_for_student
from apps.common.permissions import IsPrincipal, IsTeacher
from apps.common.responses import ok, bad  # comme ton attendance

class SpeechViewSet(ModelViewSet):
    serializer_class = SpeechSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        u = self.request.user
        qs = (
            Speech.objects
            .select_related("period", "group", "room", "student__user", "teacher__user")
            .filter(is_deleted=False)
        )

        # annotate social counts + liked_by_me
        qs = qs.annotate(
            likes_count=Count("likes", distinct=True),
            comments_count=Count("comments", distinct=True),
            liked_by_me=Exists(
                SpeechLike.objects.filter(speech_id=OuterRef("pk"), user=u)
            ),
        )

        # feed published only
        if self.action == "feed":
            return qs.filter(status="published").order_by("-published_at", "-created_at")

        # my speeches
        if getattr(u, "role", "") == "student":
            return qs.filter(student__user=u).order_by("-created_at")
        if getattr(u, "role", "") == "teacher":
            return qs.filter(teacher__user=u).order_by("-created_at")

        return qs.order_by("-created_at")

    def perform_create(self, serializer):
        u = self.request.user

        # ✅ STUDENT: derive period/group/room from enrollment (same as attendance)
        if getattr(u, "role", "") == "student":
            student = u.student_profile
            enroll, period = get_active_enrollment_for_student(student)
            if not enroll:
                raise ValueError("Not enrolled this month")  # DRF will error; better: ValidationError

            group = enroll.group
            room = group.room

            serializer.save(
                author_type="student",
                student=student,
                period=period,
                group=group,
                room=room,
                status="draft",
            )
            return

        # ✅ TEACHER: you can set period/group if you want from assignment, else keep nullable
        if getattr(u, "role", "") == "teacher":
            serializer.save(author_type="teacher", teacher=u.teacher_profile, status="draft")
            return

        serializer.save(status="draft")

    # ───────────────────────────────
    # Submit (student/teacher)
    # ───────────────────────────────
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

    # ───────────────────────────────
    # Teacher add revision
    # ───────────────────────────────
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

    # ───────────────────────────────
    # Teacher coach
    # ───────────────────────────────
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

    # ───────────────────────────────
    # Upload audio
    # ───────────────────────────────
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
        return ok({"audio": SpeechAudioSerializer(a).data}, "Audio uploaded ✅")

    # ───────────────────────────────
    # Request publish (cover required)
    # ───────────────────────────────
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

    # ───────────────────────────────
    # Principal decide
    # ───────────────────────────────
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

    # ───────────────────────────────
    # Social actions (like/comment/share/grant/feed)
    # ───────────────────────────────
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
            return bad("content is required", 400)

        c = SpeechComment.objects.create(speech=speech, user=request.user, content=content)
        return ok({"comment": {"id": c.id, "content": c.content}}, "Comment added ✅")

    @action(detail=False, methods=["get"], url_path="feed")
    def feed(self, request):
        qs = self.get_queryset()
        ser = SpeechSerializer(qs[:50], many=True, context={"request": request})
        return ok({"items": ser.data}, "Feed")
