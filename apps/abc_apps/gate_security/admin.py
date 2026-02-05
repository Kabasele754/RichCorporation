# =========================================
# apps/abc_apps/gate_security/admin.py
# =========================================
from django.contrib import admin
from apps.abc_apps.gate_security.models import GateEntry

@admin.register(GateEntry)
class GateEntryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "full_name",
        "person_type",
        "purpose",
        "check_in_at",
        "check_out_at",
        "is_overstayed_notified",
    )
    list_filter = ("person_type", "purpose", "is_overstayed_notified")
    search_fields = ("full_name", "qr_payload", "purpose_detail", "user__username", "user__email")
