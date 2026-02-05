from django.apps import AppConfig


class AccessControlConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = "apps.abc_apps.access_control"
    label = "access_control"
    verbose_name = "Access Control"
