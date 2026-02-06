# =========================================
# apps/dashboards/serializers.py
# (optional: validation/structure; not mandatory)
# =========================================
from rest_framework import serializers

class KPIItemSerializer(serializers.Serializer):
    label = serializers.CharField()
    value = serializers.IntegerField()
    trend = serializers.CharField(allow_blank=True)

class ChartSeriesSerializer(serializers.Serializer):
    name = serializers.CharField()
    data = serializers.ListField(child=serializers.IntegerField())

class ChartBlockSerializer(serializers.Serializer):
    labels = serializers.ListField(child=serializers.CharField())
    series = serializers.ListField(child=ChartSeriesSerializer())

class AlertSerializer(serializers.Serializer):
    type = serializers.CharField()
    title = serializers.CharField()
    message = serializers.CharField()
