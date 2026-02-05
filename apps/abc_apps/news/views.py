# =========================
# apps/news/views.py
# =========================
from rest_framework.viewsets import ModelViewSet, ViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action

from commons.responses import ok, fail
from commons.permissions import IsSecretary, IsPrincipal
from apps.abc_apps.news.models import NewsPost
from apps.abc_apps.news.serializers import NewsPostSerializer, PublishSerializer

class NewsPostViewSet(ModelViewSet):
    queryset = NewsPost.objects.all().order_by("-published_at", "-created_at")
    serializer_class = NewsPostSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def get_queryset(self):
        qs = super().get_queryset()
        # Students see only published
        if getattr(self.request.user, "role", "") == "student":
            return qs.filter(is_published=True)
        return qs

class NewsActionsViewSet(ViewSet):
    permission_classes = [IsAuthenticated, (IsSecretary | IsPrincipal)]

    @action(detail=False, methods=["post"])
    def publish(self, request):
        ser = PublishSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            post = NewsPost.objects.get(id=ser.validated_data["news_id"])
            post.publish()
            return ok(NewsPostSerializer(post).data, message="News published")
        except Exception as e:
            return fail(str(e), status=400)
