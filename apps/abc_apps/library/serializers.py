# =========================================
# apps/library/serializers.py
# =========================================
from rest_framework import serializers
from apps.abc_apps.library.models import Item, Loan
from apps.abc_apps.library.models_notifications import Notification

class ItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = "__all__"

class LoanSerializer(serializers.ModelSerializer):
    item = ItemSerializer(read_only=True)

    class Meta:
        model = Loan
        fields = "__all__"

class BorrowRequestSerializer(serializers.Serializer):
    item_code = serializers.CharField(max_length=50)
    purpose = serializers.ChoiceField(choices=[("reading","reading"),("class_use","class_use"),("prep","prep"),("other","other")])
    purpose_detail = serializers.CharField(max_length=255, required=False, allow_blank=True)
    due_at = serializers.DateTimeField(required=False)  # optional

class ReturnRequestSerializer(serializers.Serializer):
    item_code = serializers.CharField(max_length=50)

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = "__all__"

class MarkNotificationReadSerializer(serializers.Serializer):
    notification_id = serializers.IntegerField()
