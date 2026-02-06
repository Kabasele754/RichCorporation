# =========================================
# apps/dashboards/services/utils.py
# =========================================
from datetime import timedelta
from django.utils import timezone

def today_date():
    return timezone.localdate()

def now_dt():
    return timezone.now()

def last_n_days_dates(n: int):
    """
    Return list of dates, oldest -> newest, length n
    """
    t = today_date()
    return [t - timedelta(days=i) for i in range(n - 1, -1, -1)]

def weekday_labels(dates):
    return [d.strftime("%a") for d in dates]
