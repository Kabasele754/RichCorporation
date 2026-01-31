from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PostPublicListAPI, PostPublicDetailAPI, PostAdminViewSet

router = DefaultRouter()
router.register(r"admin/posts", PostAdminViewSet, basename="admin-posts")

urlpatterns = [
    path("posts/", PostPublicListAPI.as_view(), name="post-list"),
    path("posts/<slug:slug>/", PostPublicDetailAPI.as_view(), name="post-detail"),
    path("", include(router.urls)),
]
