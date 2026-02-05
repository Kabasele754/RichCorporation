# =========================================
# apps/abc_apps/access_control/serializers.py
# =========================================
from rest_framework import serializers
from apps.abc_apps.access_control.models import Credential, AccessPoint, AccessRule, AccessLog

class CredentialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Credential
        fields = "__all__"

class AccessPointSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessPoint
        fields = "__all__"

class AccessRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessRule
        fields = "__all__"

class AccessLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessLog
        fields = "__all__"

class ScanRequestSerializer(serializers.Serializer):
    uid = serializers.CharField(max_length=120)
    access_point_id = serializers.IntegerField()
    method = serializers.ChoiceField(choices=[("qr", "qr"), ("nfc", "nfc"), ("manual", "manual")], required=False)

class ScanResponseSerializer(serializers.Serializer):
    allowed = serializers.BooleanField()
    reason = serializers.CharField()
    access_log_id = serializers.IntegerField()
    person_name = serializers.CharField(required=False)
    role = serializers.CharField(required=False)
    person_type = serializers.CharField(required=False)  # visitor
