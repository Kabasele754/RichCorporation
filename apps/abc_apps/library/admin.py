# =========================================
# apps/library/admin.py
# =========================================
from django.contrib import admin
from apps.abc_apps.library.models import Item, Loan
from apps.abc_apps.library.models_notifications import Notification

@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("code", "item_type", "title", "status", "level_hint")
    list_filter = ("item_type", "status")
    search_fields = ("code", "title", "level_hint")

@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ("item", "borrowed_by", "purpose", "borrowed_at", "due_at", "returned_at")
    list_filter = ("purpose",)
    search_fields = ("item__code", "item__title", "borrowed_by__username", "borrowed_by__email")

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "title", "is_read", "created_at")
    list_filter = ("is_read",)
    search_fields = ("user__username", "user__email", "title")
