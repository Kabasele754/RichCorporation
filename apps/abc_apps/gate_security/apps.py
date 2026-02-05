from django.apps import AppConfig


class GateSecurityConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = "apps.abc_apps.gate_security"
    label = "gate_security"
    verbose_name = "Gate Security"
