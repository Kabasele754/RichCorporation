from rest_framework import serializers
import bleach
from .models import Post

ALLOWED_TAGS = ["p","br","strong","em","ul","ol","li","a","h2","h3","blockquote"]
ALLOWED_ATTRS = {"a": ["href", "title", "target", "rel"]}

def _img_url(request, f):
    if not f:
        return None
    if request:
        return request.build_absolute_uri(f.url)
    return f.url

class PostPublicListSerializer(serializers.ModelSerializer):
    title = serializers.CharField()
    excerpt = serializers.CharField()
    cover_image = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = ["slug", "category", "published_at", "title", "excerpt", "cover_image"]

    def get_cover_image(self, obj):
        request = self.context.get("request")
        # Prefer optimized thumb
        return _img_url(request, obj.cover_thumb_webp or obj.cover_webp or obj.cover_image)

class PostPublicDetailSerializer(serializers.ModelSerializer):
    title = serializers.CharField()
    excerpt = serializers.CharField()
    content = serializers.CharField()
    content_html = serializers.SerializerMethodField()
    cover_image = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = ["slug", "category", "published_at", "title", "excerpt", "content", "content_html", "cover_image"]

    def get_cover_image(self, obj):
        request = self.context.get("request")
        return _img_url(request, obj.cover_webp or obj.cover_image)

    def get_content_html(self, obj):
        safe = bleach.clean(obj.content or "", tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, strip=True)
        return safe.replace("\n", "<br/>")

class PostAdminSerializer(serializers.ModelSerializer):
    """
    CRUD serializer for admin endpoints.
    Uses translated fields in current activated language (lang from query).
    """
    title = serializers.CharField(required=True)
    excerpt = serializers.CharField(required=False, allow_blank=True)
    content = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Post
        fields = [
            "id", "slug", "category", "published", "published_at",
            "title", "excerpt", "content",
            "cover_image", "cover_webp", "cover_thumb_webp",
            "created_at", "updated_at",
        ]
        read_only_fields = ["cover_webp", "cover_thumb_webp", "created_at", "updated_at"]
