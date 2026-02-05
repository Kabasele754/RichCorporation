# =========================
# apps/speeches/serializers.py
# =========================
from rest_framework import serializers
from apps.abc_apps.speeches.models import Speech, SpeechCorrection, SpeechCoaching, SpeechScore, SpeechPublicationDecision

class SpeechSerializer(serializers.ModelSerializer):
    class Meta:
        model = Speech
        fields = "__all__"

class SpeechCorrectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpeechCorrection
        fields = "__all__"

class SpeechCoachingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpeechCoaching
        fields = "__all__"

class SpeechScoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpeechScore
        fields = "__all__"

class SpeechPublicationDecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpeechPublicationDecision
        fields = "__all__"

class SubmitSpeechSerializer(serializers.Serializer):
    speech_id = serializers.IntegerField()

class CorrectionRequestSerializer(serializers.Serializer):
    speech_id = serializers.IntegerField()
    corrected_content = serializers.CharField()
    correction_notes = serializers.CharField(required=False, allow_blank=True)

class CoachingRequestSerializer(serializers.Serializer):
    speech_id = serializers.IntegerField()
    pronunciation_notes = serializers.CharField(required=False, allow_blank=True)

class ScoreRequestSerializer(serializers.Serializer):
    speech_id = serializers.IntegerField()
    score = serializers.IntegerField(min_value=0, max_value=100)
    comments = serializers.CharField(required=False, allow_blank=True)

class DecisionRequestSerializer(serializers.Serializer):
    speech_id = serializers.IntegerField()
    decision = serializers.ChoiceField(choices=[("publish", "publish"), ("reject", "reject")])
    reason = serializers.CharField(required=False, allow_blank=True)
