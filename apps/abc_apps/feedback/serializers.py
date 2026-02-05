# =========================
# apps/feedback/serializers.py
# =========================
from rest_framework import serializers
from apps.abc_apps.feedback.models import TeacherRemark, MonthlyStudentReport

class TeacherRemarkSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeacherRemark
        fields = "__all__"

class MonthlyStudentReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = MonthlyStudentReport
        fields = "__all__"
