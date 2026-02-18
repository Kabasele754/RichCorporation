from datetime import datetime, timedelta
from django.utils import timezone

def compute_status(group, today, server_dt, client_dt=None):
    """
    present si scan <= start_time + grace
    late sinon
    """
    # combine today + start_time (timezone aware)
    start_naive = datetime.combine(today, group.start_time)
    start_dt = timezone.make_aware(start_naive, timezone.get_current_timezone())

    late_limit = start_dt + timedelta(minutes=group.late_grace_min)

    # source de décision: serveur (safe)
    ref = server_dt

    return "present" if ref <= late_limit else "late"
