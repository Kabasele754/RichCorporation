# =========================
# apps/news/models.py
# =========================
from django.conf import settings
from django.db import models
from django.utils import timezone
from apps.common.models import TimeStampedModel

class NewsPost(TimeStampedModel):
    title = models.CharField(max_length=160)
    body = models.TextField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["is_published", "published_at"])]

    def publish(self):
        self.is_published = True
        self.published_at = timezone.now()
        self.save(update_fields=["is_published", "published_at"])
