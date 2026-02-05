# =========================================
# apps/abc_apps/access_control/admin.py
# =========================================
from django.contrib import admin
from apps.abc_apps.access_control.models import Credential, AccessPoint, AccessRule, AccessLog

@admin.register(Credential)
class CredentialAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "cred_type", "uid", "status", "issued_at")
    list_filter = ("cred_type", "status")
    search_fields = ("uid", "user__username", "user__email")

@admin.register(AccessPoint)
class AccessPointAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "point_type", "classroom", "is_active")
    list_filter = ("point_type", "is_active")
    search_fields = ("name",)

@admin.register(AccessRule)
class AccessRuleAdmin(admin.ModelAdmin):
    list_display = ("id", "access_point", "role", "allow", "start_time", "end_time")
    list_filter = ("role", "allow")
    search_fields = ("access_point__name",)

@admin.register(AccessLog)
class AccessLogAdmin(admin.ModelAdmin):
    list_display = ("id", "access_point", "uid", "allowed", "method", "scanned_at")
    list_filter = ("allowed", "method", "access_point")
    search_fields = ("uid", "user__username", "visitor_entry__full_name")
