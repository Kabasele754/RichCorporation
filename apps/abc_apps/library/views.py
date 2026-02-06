# =========================================
# apps/library/views.py
# =========================================
from rest_framework.viewsets import ModelViewSet, ViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework import status
from django.utils import timezone

from common.responses import ok, fail
from apps.abc_apps.library.models import Item, Loan
from apps.abc_apps.library.models_notifications import Notification
from apps.abc_apps.library.serializers import (
    ItemSerializer, LoanSerializer,
    BorrowRequestSerializer, ReturnRequestSerializer,
    NotificationSerializer, MarkNotificationReadSerializer
)
from apps.abc_apps.library.permissions import IsTeacherOrSecretaryOrStaff
from apps.abc_apps.library.services.loan import borrow_item, return_item
from apps.abc_apps.library.services.reminders import send_reading_reminders, send_return_reminders

class ItemViewSet(ModelViewSet):
    queryset = Item.objects.all().order_by("item_type", "title")
    serializer_class = ItemSerializer
    permission_classes = [IsAuthenticated, IsTeacherOrSecretaryOrStaff]

class LoanViewSet(ViewSet):
    """
    Endpoints:
    - POST /api/library/loans/borrow/
    - POST /api/library/loans/return/
    - GET  /api/library/loans/my/
    - GET  /api/library/loans/open/   (staff only)
    """
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["post"], url_path="borrow", permission_classes=[IsAuthenticated])
    def borrow(self, request):
        ser = BorrowRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        item_code = ser.validated_data["item_code"]
        purpose = ser.validated_data["purpose"]
        purpose_detail = ser.validated_data.get("purpose_detail", "")
        due_at = ser.validated_data.get("due_at")

        try:
            loan = borrow_item(
                item_code=item_code,
                borrowed_by=request.user,
                issued_by=request.user,  # desk issuer = same user; you can change later
                purpose=purpose,
                purpose_detail=purpose_detail,
                due_at=due_at,
            )
            return ok(LoanSerializer(loan).data, message="Borrowed", status=status.HTTP_201_CREATED)
        except Exception as e:
            return fail(str(e), status=400)

    @action(detail=False, methods=["post"], url_path="return", permission_classes=[IsAuthenticated])
    def return_(self, request):
        ser = ReturnRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        item_code = ser.validated_data["item_code"]

        try:
            loan = return_item(item_code=item_code, return_checked_by=request.user)
            return ok(LoanSerializer(loan).data, message="Returned", status=status.HTTP_200_OK)
        except Exception as e:
            return fail(str(e), status=400)

    @action(detail=False, methods=["get"], url_path="my")
    def my_loans(self, request):
        qs = Loan.objects.select_related("item").filter(borrowed_by=request.user).order_by("-borrowed_at")
        return ok(LoanSerializer(qs, many=True).data)

    @action(detail=False, methods=["get"], url_path="open", permission_classes=[IsAuthenticated, IsTeacherOrSecretaryOrStaff])
    def open_loans(self, request):
        qs = Loan.objects.select_related("item", "borrowed_by").filter(returned_at__isnull=True).order_by("-borrowed_at")
        return ok(LoanSerializer(qs, many=True).data)


class NotificationViewSet(ViewSet):
    """
    - GET  /api/library/notifications/my/
    - POST /api/library/notifications/mark-read/
    """
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["get"], url_path="my")
    def my_notifications(self, request):
        qs = Notification.objects.filter(user=request.user).order_by("-created_at")[:200]
        return ok(NotificationSerializer(qs, many=True).data)

    @action(detail=False, methods=["post"], url_path="mark-read")
    def mark_read(self, request):
        ser = MarkNotificationReadSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        nid = ser.validated_data["notification_id"]

        try:
            n = Notification.objects.get(id=nid, user=request.user)
            n.is_read = True
            n.save(update_fields=["is_read"])
            return ok({"notification_id": n.id, "is_read": True}, message="Marked as read")
        except Notification.DoesNotExist:
            return fail("Notification not found", status=404)


class ReminderViewSet(ViewSet):
    """
    Simple trigger (no celery):
    - POST /api/library/reminders/run/
    """
    permission_classes = [IsAuthenticated, IsTeacherOrSecretaryOrStaff]

    @action(detail=False, methods=["post"], url_path="run")
    def run(self, request):
        try:
            send_reading_reminders()
            send_return_reminders()
            return ok({"ran_at": timezone.now().isoformat()}, message="Reminders executed")
        except Exception as e:
            return fail(str(e), status=400)
