from django.utils.translation import activate
from django.core.cache import cache

from rest_framework import generics, viewsets, permissions
from rest_framework.response import Response
from rest_framework.decorators import action

from apps.blog.models import Post
from apps.blog.pagination import PostPagination
from apps.blog.serializers import (
    PostPublicListSerializer,
    PostPublicDetailSerializer,
    PostAdminSerializer,
)

def get_lang(request):
    lang = request.query_params.get("lang", "fr").lower()
    return "en" if lang.startswith("en") else "fr"

# ---------- PUBLIC (read-only) ----------
class PostPublicListAPI(generics.ListAPIView):
    serializer_class = PostPublicListSerializer
    pagination_class = PostPagination

    filterset_fields = ["category"]
    search_fields = [
        "translations__title",
        "translations__excerpt",
        "translations__content",
    ]
    ordering_fields = ["published_at", "created_at"]
    ordering = ["-published_at"]

    def get_queryset(self):
        lang = get_lang(self.request)
        activate(lang)

        qs = (
            Post.objects
            .filter(published=True)
            .language(lang)
            .order_by("-published_at")
        )

        category = self.request.query_params.get("category")
        if category and category != "all":
            qs = qs.filter(category=category)

        return qs

    def list(self, request, *args, **kwargs):
        lang = get_lang(request)

        # ⚠️ important : inclure page, category, search, etc.
        cache_key = f"posts:list:{lang}:{request.query_params.urlencode()}"
        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        response = super().list(request, *args, **kwargs)

        # cache 5 minutes
        cache.set(cache_key, response.data, 60 * 5)
        return response



class PostPublicDetailAPI(generics.RetrieveAPIView):
    serializer_class = PostPublicDetailSerializer
    lookup_field = "slug"

    def get_queryset(self):
        lang = get_lang(self.request)
        activate(lang)
        return Post.objects.filter(published=True).language(lang)

    def retrieve(self, request, *args, **kwargs):
        lang = get_lang(request)
        slug = kwargs.get("slug")
        key = f"posts:detail:{lang}:{slug}"
        cached = cache.get(key)
        if cached:
            return Response(cached)

        resp = super().retrieve(request, *args, **kwargs)
        cache.set(key, resp.data, 60 * 10)  # 10 min
        return resp


# ---------- ADMIN CRUD (protected) ----------
class IsAdminOrStaff(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.is_staff or request.user.is_superuser)
        )


class PostAdminViewSet(viewsets.ModelViewSet):
    """
    CRUD for admins:
    - GET/POST/PUT/PATCH/DELETE /api/v1/admin/posts/
    - Uses lang query param to edit specific translation (fr or en)
    """
    queryset = Post.objects.all()
    serializer_class = PostAdminSerializer
    permission_classes = [IsAdminOrStaff]
    filterset_fields = ["category", "published"]
    search_fields = ["translations__title", "translations__excerpt", "translations__content", "slug"]
    ordering_fields = ["published_at", "created_at", "updated_at"]
    ordering = ["-published_at"]

    def initial(self, request, *args, **kwargs):
        activate(get_lang(request))
        super().initial(request, *args, **kwargs)

    def perform_create(self, serializer):
        obj = serializer.save()
        self._invalidate_cache(obj)

    def perform_update(self, serializer):
        obj = serializer.save()
        self._invalidate_cache(obj)

    def perform_destroy(self, instance):
        self._invalidate_cache(instance)
        instance.delete()

    @action(detail=False, methods=["post"], url_path="clear-cache")
    def clear_cache(self, request):
        cache.clear()
        return Response({"ok": True})

    def _invalidate_cache(self, obj: Post):
        if hasattr(cache, "delete_pattern"):
            cache.delete_pattern("posts:list:*")
        else:
            cache.clear()

        for lang in ("fr", "en"):
            cache.delete(f"posts:detail:{lang}:{obj.slug}")
