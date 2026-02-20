# =========================
# apps/speeches/admin.py
# =========================
from django.contrib import admin
from apps.abc_apps.speeches.models import Speech, SpeechApproval, SpeechAudio,  SpeechCoaching

admin.site.register(Speech)
admin.site.register(SpeechCoaching)
admin.site.register(SpeechAudio)
admin.site.register(SpeechApproval)

