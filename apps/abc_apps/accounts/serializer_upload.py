from rest_framework import serializers
from apps.abc_apps.accounts.models import User

class ProfilePhotoUploadSerializer(serializers.Serializer):
    photo = serializers.ImageField()

    def validate_photo(self, f):
        # ✅ validation minimale (taille + type)
        max_mb = 5
        if f.size > max_mb * 1024 * 1024:
            raise serializers.ValidationError(f"Max file size is {max_mb}MB")

        name = (f.name or "").lower()
        if not (name.endswith(".jpg") or name.endswith(".jpeg") or name.endswith(".png") or name.endswith(".webp")):
            raise serializers.ValidationError("Only JPG, PNG, WEBP allowed")

        return f
