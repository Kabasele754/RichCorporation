# =========================
# apps/news/serializers.py
# =========================
from rest_framework import serializers
from apps.abc_apps.news.models import NewsPost

class NewsPostSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewsPost
        fields = "__all__"

class PublishSerializer(serializers.Serializer):
    news_id = serializers.IntegerField()
