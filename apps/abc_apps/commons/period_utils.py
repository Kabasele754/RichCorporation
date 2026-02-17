from datetime import date


def next_month(d: date) -> date:
    y, m = d.year, d.month
    if m == 12:
        return date(y + 1, 1, 1)
    return date(y, m + 1, 1)


def monday_of(d: date) -> date:
    return d - __import__("datetime").timedelta(days=d.weekday())
