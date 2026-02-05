# =========================
# apps/exams/serializers.py
# =========================
from rest_framework import serializers
from apps.abc_apps.exams.models import ExamRuleStatus, ExamEntryScan, MonthlyReturnForm

class ExamRuleStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExamRuleStatus
        fields = "__all__"

class ExamEntryScanSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExamEntryScan
        fields = "__all__"

class MonthlyReturnFormSerializer(serializers.ModelSerializer):
    class Meta:
        model = MonthlyReturnForm
        fields = "__all__"

class ExamEntryScanRequestSerializer(serializers.Serializer):
    qr_payload = serializers.CharField(max_length=255)

class ReturnFormRequestSerializer(serializers.Serializer):
    month = serializers.CharField(max_length=7)
    will_return = serializers.BooleanField()
    reason_if_no = serializers.CharField(required=False, allow_blank=True)
