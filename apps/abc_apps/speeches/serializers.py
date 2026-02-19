# apps/abc_apps/speeches/serializers.py
from __future__ import annotations
from django.db.models import Count
from rest_framework import serializers

from apps.abc_apps.speeches.models import (
    Speech, SpeechRevision, SpeechCoaching, SpeechAudio,
    SpeechApproval, SpeechComment
)

class SpeechAudioSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = SpeechAudio
        fields = ["id", "kind", "url", "duration_sec", "created_at", "engine", "voice_name", "is_primary"]

    def get_url(self, obj):
        request = self.context.get("request")
        if not obj.audio_file:
            return None
        url = obj.audio_file.url
        return request.build_absolute_uri(url) if request else url


class SpeechRevisionSerializer(serializers.ModelSerializer):
    revised_by_name = serializers.SerializerMethodField()

    class Meta:
        model = SpeechRevision
        fields = ["id", "version", "revised_content", "notes", "is_final", "revised_by_name", "created_at"]

    def get_revised_by_name(self, obj):
        u = obj.revised_by
        if not u:
            return None
        return f"{getattr(u,'first_name','')}".strip() or getattr(u, "email", "")


class SpeechCoachingSerializer(serializers.ModelSerializer):
    teacher_name = serializers.SerializerMethodField()

    class Meta:
        model = SpeechCoaching
        fields = ["id", "pronunciation_notes", "word_tips", "is_final", "teacher_name", "created_at"]

    def get_teacher_name(self, obj):
        t = obj.teacher
        if not t or not getattr(t, "user", None):
            return None
        u = t.user
        return f"{getattr(u,'first_name','')} {getattr(u,'last_name','')}".strip()


class SpeechSerializer(serializers.ModelSerializer):
    period_key = serializers.CharField(source="period.key", read_only=True)
    group_label = serializers.CharField(source="group.label", read_only=True)
    room_code = serializers.CharField(source="room.code", read_only=True)

    # ✅ level info from MonthlyClassGroup
    level_id = serializers.IntegerField(source="group.level_id", read_only=True)
    level_label = serializers.CharField(source="group.level.label", read_only=True)

    audios = SpeechAudioSerializer(many=True, read_only=True)
    revisions = SpeechRevisionSerializer(many=True, read_only=True)
    coachings = SpeechCoachingSerializer(many=True, read_only=True)

    likes_count = serializers.IntegerField(read_only=True)
    comments_count = serializers.IntegerField(read_only=True)
    liked_by_me = serializers.BooleanField(read_only=True)

    author_name = serializers.SerializerMethodField()

    class Meta:
        model = Speech
        fields = [
            "id",
            "period", "group", "room",
            "period_key", "group_label", "room_code",
            "level_id", "level_label",
            "author_type", "student", "teacher",
            "author_name",
            "month",
            "category",
            "title", "raw_content",
            "cover_image",
            "status", "visibility",
            "submitted_at", "published_at",
            "likes_count", "comments_count", "liked_by_me",
            "audios", "revisions", "coachings",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "period", "group", "room",
            "student", "teacher", "author_type",
            "status", "submitted_at", "published_at",
        ]

    def get_author_name(self, obj):
        if obj.author_type == "student" and obj.student and getattr(obj.student, "user", None):
            u = obj.student.user
            return f"{u.first_name} {u.last_name}".strip() or u.email
        if obj.author_type == "teacher" and obj.teacher and getattr(obj.teacher, "user", None):
            u = obj.teacher.user
            return f"{u.first_name} {u.last_name}".strip() or u.email
        return None


class SpeechApprovalSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpeechApproval
        fields = ["id", "speech", "decided_by", "decision", "reason", "decided_at"]
        read_only_fields = ["decided_by", "decided_at"]


class SpeechCommentSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = SpeechComment
        fields = ["id", "speech", "user", "user_name", "content", "is_hidden", "created_at"]
        read_only_fields = ["user", "is_hidden"]

    def get_user_name(self, obj):
        return obj.user.get_full_name() if obj.user_id else ""

# Petite réponse pour actions
class SimpleMessageSerializer(serializers.Serializer):
    message = serializers.CharField()
