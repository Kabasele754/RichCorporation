# =========================================
# apps/abc_apps/gate_security/services/overstay.py
# =========================================
from datetime import timedelta
from django.utils import timezone
from apps.abc_apps.gate_security.models import GateEntry

def get_open_entries():
    return GateEntry.objects.filter(check_out_at__isnull=True).order_by("-check_in_at")

def get_overstays(minutes: int = 30):
    limit = timezone.now() - timedelta(minutes=minutes)
    return GateEntry.objects.filter(
        check_out_at__isnull=True,
        check_in_at__lte=limit,
    ).order_by("check_in_at")

def get_overstays_to_notify(minutes: int = 30):
    limit = timezone.now() - timedelta(minutes=minutes)
    return GateEntry.objects.filter(
        check_out_at__isnull=True,
        check_in_at__lte=limit,
        is_overstayed_notified=False,
    ).order_by("check_in_at")

def mark_notified(entry: GateEntry):
    entry.is_overstayed_notified = True
    entry.overstayed_notified_at = timezone.now()
    entry.save(update_fields=["is_overstayed_notified", "overstayed_notified_at"])
    return entry
