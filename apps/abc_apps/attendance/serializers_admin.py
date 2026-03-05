from rest_framework import serializers
from apps.abc_apps.academics.models import Room, SchoolCampus
from .models import RoomScanTag


class SchoolCampusSerializer(serializers.ModelSerializer):
    address_full = serializers.CharField(read_only=True)

    class Meta:
        model = SchoolCampus
        fields = "__all__"


class RoomSerializer(serializers.ModelSerializer):
    campus_name = serializers.CharField(source="campus.name", read_only=True)

    class Meta:
        model = Room
        fields = ["id", "code", "name", "capacity", "is_active", "campus", "campus_name"]


class RoomScanTagSerializer(serializers.ModelSerializer):
    room_code = serializers.CharField(source="room.code", read_only=True)
    room_name = serializers.CharField(source="room.name", read_only=True)

    class Meta:
        model = RoomScanTag
        fields = [
            "id",
            "room", "room_code", "room_name",
            "latitude", "longitude", "radius_m",
            "is_active", "created_at", "updated_at",
        ]