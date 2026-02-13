# users/views.py
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework import serializers

from .serializers import MeSerializer
from apps.common.responses import ok, fail


class MeLocationSerializer(serializers.Serializer):
    lat = serializers.DecimalField(max_digits=9, decimal_places=6)
    lng = serializers.DecimalField(max_digits=9, decimal_places=6)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def me_location_update(request):
    ser = MeLocationSerializer(data=request.data)
    ser.is_valid(raise_exception=True)

    u = request.user
    u.lat = ser.validated_data["lat"]
    u.lng = ser.validated_data["lng"]
    u.location_updated_at = timezone.now()
    u.save(update_fields=["lat", "lng", "location_updated_at"])

    return ok(MeSerializer(u).data)
