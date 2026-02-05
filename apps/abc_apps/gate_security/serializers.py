# =========================================
# apps/abc_apps/gate_security/serializers.py
# =========================================
from django.contrib.auth import get_user_model
from rest_framework import serializers
from apps.abc_apps.gate_security.models import GateEntry

User = get_user_model()

def _person_type_from_role(role: str) -> str:
    if role == "teacher":
        return "teacher"
    if role == "secretary":
        return "secretary"
    if role == "principal":
        return "principal"
    return "staff"

class GateEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = GateEntry
        fields = "__all__"
        read_only_fields = ["checked_by", "is_overstayed_notified", "overstayed_notified_at", "created_at", "updated_at"]

class GateCheckInSerializer(serializers.Serializer):
    """
    Check-in peut venir de:
    - Un user connu (user_id) => on auto-remplit full_name/person_type
    - Un visitor (full_name + person_type=visitor)
    """
    user_id = serializers.IntegerField(required=False)
    full_name = serializers.CharField(max_length=160, required=False)
    person_type = serializers.ChoiceField(choices=GateEntry.PERSON_TYPE, required=False)

    purpose = serializers.ChoiceField(choices=GateEntry.PURPOSE)
    purpose_detail = serializers.CharField(max_length=255, required=False, allow_blank=True)

    signature_base64 = serializers.CharField(required=False, allow_blank=True)
    qr_payload = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def validate(self, attrs):
        user_id = attrs.get("user_id")
        full_name = attrs.get("full_name")
        person_type = attrs.get("person_type")

        if not user_id and not full_name:
            raise serializers.ValidationError("Provide user_id (known staff) OR full_name (visitor).")

        if full_name and not person_type:
            # default visitor if name is provided
            attrs["person_type"] = "visitor"

        return attrs

    def create(self, validated_data):
        user_id = validated_data.get("user_id")
        if user_id:
            user = User.objects.get(id=user_id)
            role = getattr(user, "role", "")
            full_name = (f"{user.first_name} {user.last_name}").strip() or user.username
            person_type = _person_type_from_role(role)

            return GateEntry.objects.create(
                user=user,
                full_name=full_name,
                person_type=person_type,
                purpose=validated_data["purpose"],
                purpose_detail=validated_data.get("purpose_detail", ""),
                signature_base64=validated_data.get("signature_base64", ""),
                qr_payload=validated_data.get("qr_payload", ""),
            )

        # visitor mode
        return GateEntry.objects.create(
            full_name=validated_data["full_name"],
            person_type=validated_data.get("person_type", "visitor"),
            purpose=validated_data["purpose"],
            purpose_detail=validated_data.get("purpose_detail", ""),
            signature_base64=validated_data.get("signature_base64", ""),
            qr_payload=validated_data.get("qr_payload", ""),
        )

class GateCheckOutSerializer(serializers.Serializer):
    entry_id = serializers.IntegerField()

class GateOverstayQuerySerializer(serializers.Serializer):
    minutes = serializers.IntegerField(required=False, min_value=5, max_value=24*60)
