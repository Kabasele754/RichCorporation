# =========================
# apps/speeches/views.py
# =========================
from rest_framework.viewsets import ModelViewSet, ViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action

from commons.responses import ok, fail
from commons.permissions import IsTeacher, IsPrincipal, IsStudent
from apps.abc_apps.speeches.models import Speech
from apps.abc_apps.speeches.serializers import (
    SpeechSerializer,
    SubmitSpeechSerializer, CorrectionRequestSerializer, CoachingRequestSerializer,
    ScoreRequestSerializer, DecisionRequestSerializer
)
from apps.abc_apps.speeches.services.workflow import submit_speech, apply_correction, apply_coaching, score_speech, decide_publication

class SpeechViewSet(ModelViewSet):
    queryset = Speech.objects.select_related("student").all().order_by("-month", "-created_at")
    serializer_class = SpeechSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        # student sees only his speeches
        if getattr(self.request.user, "role", "") == "student" and hasattr(self.request.user, "student_profile"):
            return qs.filter(student=self.request.user.student_profile)
        return qs

class SpeechActionsViewSet(ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated, IsStudent])
    def submit(self, request):
        ser = SubmitSpeechSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            sp = Speech.objects.get(id=ser.validated_data["speech_id"], student=request.user.student_profile)
            submit_speech(sp)
            return ok(SpeechSerializer(sp).data, message="Speech submitted")
        except Exception as e:
            return fail(str(e), status=400)

    @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated, IsTeacher])
    def correct(self, request):
        ser = CorrectionRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            sp = Speech.objects.get(id=ser.validated_data["speech_id"])
            apply_correction(sp, request.user.teacher_profile, ser.validated_data["corrected_content"], ser.validated_data.get("correction_notes", ""))
            return ok(SpeechSerializer(sp).data, message="Speech corrected")
        except Exception as e:
            return fail(str(e), status=400)

    @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated, IsTeacher])
    def coach(self, request):
        ser = CoachingRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            sp = Speech.objects.get(id=ser.validated_data["speech_id"])
            apply_coaching(sp, request.user.teacher_profile, ser.validated_data.get("pronunciation_notes", ""))
            return ok(SpeechSerializer(sp).data, message="Speech coached")
        except Exception as e:
            return fail(str(e), status=400)

    @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated, IsTeacher])
    def score(self, request):
        ser = ScoreRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            sp = Speech.objects.get(id=ser.validated_data["speech_id"])
            score_speech(sp, request.user.teacher_profile, ser.validated_data["score"], ser.validated_data.get("comments", ""))
            return ok(SpeechSerializer(sp).data, message="Speech scored")
        except Exception as e:
            return fail(str(e), status=400)

    @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated, IsPrincipal])
    def decide(self, request):
        ser = DecisionRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            sp = Speech.objects.get(id=ser.validated_data["speech_id"])
            decide_publication(sp, request.user, ser.validated_data["decision"], ser.validated_data.get("reason", ""))
            return ok(SpeechSerializer(sp).data, message="Decision saved")
        except Exception as e:
            return fail(str(e), status=400)
