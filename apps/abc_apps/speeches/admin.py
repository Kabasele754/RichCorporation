# =========================
# apps/speeches/admin.py
# =========================
from django.contrib import admin
from apps.abc_apps.speeches.models import Speech, SpeechCorrection, SpeechCoaching, SpeechScore, SpeechPublicationDecision

admin.site.register(Speech)
admin.site.register(SpeechCorrection)
admin.site.register(SpeechCoaching)
admin.site.register(SpeechScore)
admin.site.register(SpeechPublicationDecision)
