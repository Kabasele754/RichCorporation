from datetime import date
from apps.abc_apps.academics.models import AcademicPeriod


def get_or_create_period_from_date(d: date) -> AcademicPeriod:
    """
    Suppose AcademicPeriod a: year, month, key (ex: '2026-02')
    """
    y, m = d.year, d.month
    key = f"{y}-{str(m).zfill(2)}"
    obj, _ = AcademicPeriod.objects.get_or_create(
        key=key,
        defaults={"year": y, "month": m},
    )
    return obj



