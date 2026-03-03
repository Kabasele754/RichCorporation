# =========================
# apps/speeches/admin.py
# =========================
from django.contrib import admin
from apps.abc_apps.speeches.models import Speech, SpeechApproval, SpeechAudio,  SpeechCoaching, SpeechComment, SpeechLike, SpeechRevision

admin.site.register(Speech)
admin.site.register(SpeechCoaching)
admin.site.register(SpeechAudio)
admin.site.register(SpeechApproval)
admin.site.register(SpeechLike)
admin.site.register(SpeechComment)
admin.site.register(SpeechRevision)


