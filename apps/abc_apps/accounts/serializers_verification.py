from rest_framework import serializers
from .models_verification import VerificationDocument


class VerificationUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = VerificationDocument
        fields = ("doc_type", "document_number", "country_of_issue", "expiry_date", "document")

    def validate_document(self, f):
        # ✅ taille max 5MB (tu peux changer)
        max_bytes = 5 * 1024 * 1024
        if f.size > max_bytes:
            raise serializers.ValidationError("File too large. Max 5MB.")
        return f


class VerificationDocSerializer(serializers.ModelSerializer):
    document_url = serializers.SerializerMethodField()

    class Meta:
        model = VerificationDocument
        fields = (
            "id",
            "doc_type",
            "document_number",
            "country_of_issue",
            "expiry_date",
            "status",
            "admin_note",
            "document_url",
            "created_at",
        )

    def get_document_url(self, obj):
        request = self.context.get("request")
        if not obj.document:
            return None
        url = obj.document.url
        return request.build_absolute_uri(url) if request else url
