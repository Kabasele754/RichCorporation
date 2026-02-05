# =========================================
# apps/abc_apps/gate_security/views.py
# =========================================
from rest_framework.viewsets import ViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework import status
from django.utils import timezone

from common.responses import ok, fail
from apps.abc_apps.gate_security.models import GateEntry
from apps.abc_apps.gate_security.serializers import (
    GateEntrySerializer,
    GateCheckInSerializer,
    GateCheckOutSerializer,
    GateOverstayQuerySerializer,
)
from apps.abc_apps.gate_security.permissions import IsSecurityOrStaff
from apps.abc_apps.gate_security.services.overstay import (
    get_open_entries,
    get_overstays,
    get_overstays_to_notify,
    mark_notified,
)

class GateSecurityViewSet(ViewSet):
    """
    Endpoints:
    - POST  /api/gate/entries/check-in/
    - POST  /api/gate/entries/check-out/
    - GET   /api/gate/entries/open/
    - GET   /api/gate/entries/overstays/?minutes=30
    - POST  /api/gate/entries/notify-overstays/   (marque notified + retourne liste)
    """
    permission_classes = [IsAuthenticated, IsSecurityOrStaff]

    @action(detail=False, methods=["post"], url_path="check-in")
    def check_in(self, request):
        ser = GateCheckInSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            entry = ser.save()
            # agent sécurité qui a enregistré
            entry.checked_by = request.user
            entry.save(update_fields=["checked_by"])
            return ok(GateEntrySerializer(entry).data, message="Gate check-in saved", status=status.HTTP_201_CREATED)
        except Exception as e:
            return fail(str(e), status=400)

    @action(detail=False, methods=["post"], url_path="check-out")
    def check_out(self, request):
        ser = GateCheckOutSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            entry = GateEntry.objects.get(id=ser.validated_data["entry_id"])
            if entry.check_out_at:
                return ok(GateEntrySerializer(entry).data, message="Already checked out")

            entry.check_out_at = timezone.now()
            entry.save(update_fields=["check_out_at"])
            return ok(GateEntrySerializer(entry).data, message="Gate check-out saved")
        except GateEntry.DoesNotExist:
            return fail("Entry not found", status=404)
        except Exception as e:
            return fail(str(e), status=400)

    @action(detail=False, methods=["get"], url_path="open")
    def open_entries(self, request):
        qs = get_open_entries()
        return ok(GateEntrySerializer(qs, many=True).data)

    @action(detail=False, methods=["get"], url_path="overstays")
    def overstays(self, request):
        ser = GateOverstayQuerySerializer(data=request.query_params)
        ser.is_valid(raise_exception=True)
        minutes = ser.validated_data.get("minutes", 30)
        qs = get_overstays(minutes=minutes)
        return ok(GateEntrySerializer(qs, many=True).data)

    @action(detail=False, methods=["post"], url_path="notify-overstays")
    def notify_overstays(self, request):
        """
        Version simple (sans Celery):
        - L'agent appelle cet endpoint (ou l'app le fait toutes les X minutes)
        - On marque is_overstayed_notified=True
        - Ensuite Flutter peut afficher "⚠️ overstays"
        """
        minutes = int(request.data.get("minutes", 30))
        try:
            qs = get_overstays_to_notify(minutes=minutes)
            notified = []
            for entry in qs:
                mark_notified(entry)
                notified.append(entry)
            return ok(GateEntrySerializer(notified, many=True).data, message="Overstays marked notified")
        except Exception as e:
            return fail(str(e), status=400)
