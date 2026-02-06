# =========================================
# apps/library/urls.py
# =========================================
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.abc_apps.library.views import ItemViewSet, LoanViewSet, NotificationViewSet, ReminderViewSet

router = DefaultRouter()
router.register(r"items", ItemViewSet, basename="library-items")
router.register(r"loans", LoanViewSet, basename="library-loans")
router.register(r"notifications", NotificationViewSet, basename="library-notifications")
router.register(r"reminders", ReminderViewSet, basename="library-reminders")

urlpatterns = [path("", include(router.urls))]
