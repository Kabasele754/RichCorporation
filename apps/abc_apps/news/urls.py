# =========================
# apps/news/urls.py
# =========================
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.abc_apps.news.views import NewsPostViewSet, NewsActionsViewSet

router = DefaultRouter()
router.register(r"posts", NewsPostViewSet)
router.register(r"actions", NewsActionsViewSet, basename="news-actions")

urlpatterns = [path("", include(router.urls))]
