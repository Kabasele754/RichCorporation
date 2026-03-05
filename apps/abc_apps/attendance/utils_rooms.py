# apps/abc_apps/attendance/utils_rooms.py
import re
from typing import Optional
from django.db import IntegrityError, transaction
from apps.abc_apps.academics.models import Room, SchoolCampus

ROOM_CODE_RE = re.compile(r"^R(\d+)$", re.IGNORECASE)

def _next_room_code_global() -> str:
    max_n = 0
    codes = Room.objects.values_list("code", flat=True)
    for c in codes:
        m = ROOM_CODE_RE.match((c or "").strip())
        if m:
            max_n = max(max_n, int(m.group(1)))
    return f"R{max_n + 1}"

def create_room_auto_code(*, campus: Optional[SchoolCampus], name: str, capacity=None, is_active=True) -> Room:
    """
    Crée une room avec code auto (retry si collision).
    Compatible Python < 3.10
    """
    for _ in range(10):
        code = _next_room_code_global()
        try:
            with transaction.atomic():
                return Room.objects.create(
                    campus=campus,
                    code=code,
                    name=name,
                    capacity=capacity,
                    is_active=is_active,
                )
        except IntegrityError:
            continue
    raise IntegrityError("Could not generate unique Room code after retries")