# =========================
# apps/speeches/urls.py
# =========================
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.abc_apps.speeches.views import SpeechViewSet

router = DefaultRouter()
router.register(r"speeches", SpeechViewSet, basename="speeches")

# speech_like = SpeechViewSet.as_view({"post": "like"})
# speech_comment = SpeechViewSet.as_view({"post": "comment"})
# speech_comments = SpeechViewSet.as_view({"get": "comments"})
# router.register(r"actions", SpeechActionsViewSet, basename="speech-actions")

urlpatterns = [
    path("", include(router.urls)),
    # path("speeches/like/", speech_like, name="speech-like"),
    # path("speeches/comment/", speech_comment, name="speech-comment"),
    # path("speeches/comments/", speech_comments, name="speech-comments"),
    
]
