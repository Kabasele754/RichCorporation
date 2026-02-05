# =========================
# apps/news/admin.py
# =========================
from django.contrib import admin
from apps.abc_apps.news.models import NewsPost

admin.site.register(NewsPost)
