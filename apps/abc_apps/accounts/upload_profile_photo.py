from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.decorators import parser_classes

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from apps.abc_apps.accounts.serializer_upload import ProfilePhotoUploadSerializer
from apps.abc_apps.accounts.serializers import MeSerializer
from apps.common.responses import ok, fail
from rest_framework import status

@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def upload_profile_photo(request):
    ser = ProfilePhotoUploadSerializer(data=request.data)
    ser.is_valid(raise_exception=True)

    u = request.user
    u.profile_photo = ser.validated_data["photo"]
    u.save(update_fields=["profile_photo"])

    return ok(MeSerializer(u, context={"request": request}).data)

@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_profile_photo(request):
    u = request.user
    if u.profile_photo:
        u.profile_photo.delete(save=False)
    u.profile_photo = None
    u.save(update_fields=["profile_photo"])
    return ok(MeSerializer(u, context={"request": request}).data)

