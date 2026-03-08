from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from django.db import transaction

from apps.abc_apps.academics.models import (
    AcademicLevel,
    AcademicPeriod,
    MonthlyClassGroup,
    Room,
    StudentMonthlyEnrollment,
)

MAX_STUDENTS_PER_GROUP = 25


def get_next_level(current_level: AcademicLevel) -> Optional[AcademicLevel]:
    """
    Trouve le niveau suivant selon l'ordre.
    Exemple:
    Foundation 1 (order=1) -> Foundation 2 (order=2)
    """
    return (
        AcademicLevel.objects
        .filter(order__gt=current_level.order)
        .order_by("order")
        .first()
    )


def group_name_from_index(index: int) -> str:
    """
    0 -> A
    1 -> B
    ...
    25 -> Z
    26 -> A2
    """
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    if index < 26:
        return alphabet[index]
    return f"{alphabet[index % 26]}{(index // 26) + 1}"


def get_candidate_rooms() -> List[Room]:
    """
    Rooms actives triées intelligemment:
    - d'abord capacité >= 25 si disponible
    - ensuite par code
    """
    rooms = list(Room.objects.filter(is_active=True).order_by("code"))
    rooms.sort(key=lambda r: (0 if (r.capacity or 0) >= MAX_STUDENTS_PER_GROUP else 1, r.code))
    return rooms


def pick_room(
    available_rooms: List[Room],
    used_room_ids: set,
    required_size: int,
) -> Optional[Room]:
    """
    Choisit une salle libre.
    Priorité:
    - salle non utilisée
    - capacité >= required_size si possible
    """
    # 1. meilleure salle adaptée
    for room in available_rooms:
        if room.id in used_room_ids:
            continue
        cap = room.capacity or 0
        if cap == 0 or cap >= required_size:
            return room

    # 2. fallback: n'importe quelle salle libre
    for room in available_rooms:
        if room.id not in used_room_ids:
            return room

    return None


def get_or_create_monthly_group(
    *,
    period: AcademicPeriod,
    level: AcademicLevel,
    group_name: str,
    room: Room,
    created_by=None,
) -> MonthlyClassGroup:
    group, _ = MonthlyClassGroup.objects.get_or_create(
        period=period,
        level=level,
        group_name=group_name,
        room=room,
        defaults={
            "is_active": True,
            "created_by": created_by,
        },
    )
    return group


def split_list(items: List, chunk_size: int) -> List[List]:
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]


def build_next_groups_for_level(
    *,
    from_period: AcademicPeriod,
    to_period: AcademicPeriod,
    current_level: AcademicLevel,
    next_level: AcademicLevel,
    enrollments: List[StudentMonthlyEnrollment],
    created_by=None,
) -> Dict[int, MonthlyClassGroup]:
    """
    Retourne un mapping:
        student_id -> MonthlyClassGroup du mois suivant

    Logique:
    - regrouper par ancien group_name
    - essayer de garder les cohortes ensemble
    - split par paquets de 25 max
    - créer les groupes suivants
    """
    old_buckets: Dict[str, List[StudentMonthlyEnrollment]] = defaultdict(list)

    for enr in enrollments:
        old_name = enr.group.group_name or "A"
        old_buckets[old_name].append(enr)

    ordered_old_names = sorted(old_buckets.keys())

    candidate_rooms = get_candidate_rooms()
    used_room_ids = set()

    result: Dict[int, MonthlyClassGroup] = {}
    new_group_index = 0

    for old_name in ordered_old_names:
        bucket = old_buckets[old_name]

        # garder ordre stable
        bucket = sorted(bucket, key=lambda x: (x.student_id, x.id))

        chunks = split_list(bucket, MAX_STUDENTS_PER_GROUP)

        for chunk in chunks:
            new_group_name = group_name_from_index(new_group_index)
            new_group_index += 1

            room = pick_room(
                available_rooms=candidate_rooms,
                used_room_ids=used_room_ids,
                required_size=len(chunk),
            )
            if not room:
                raise ValueError(
                    f"No available room found for {next_level.label} group {new_group_name}"
                )

            used_room_ids.add(room.id)

            monthly_group = get_or_create_monthly_group(
                period=to_period,
                level=next_level,
                group_name=new_group_name,
                room=room,
                created_by=created_by,
            )

            for enr in chunk:
                result[enr.student_id] = monthly_group

    return result


@transaction.atomic
def promote_students_for_next_period(
    *,
    from_period: AcademicPeriod,
    to_period: AcademicPeriod,
    student_ids: List[int],
    created_by=None,
) -> Dict[str, int]:
    """
    Promotion intelligente:
    - lit les enrollments actifs du mois courant
    - détecte le next level
    - crée les groupes mensuels du mois suivant
    - crée les StudentMonthlyEnrollment
    """
    current_enrollments = list(
        StudentMonthlyEnrollment.objects
        .select_related("group", "group__level", "group__room")
        .filter(
            period=from_period,
            student_id__in=student_ids,
            status="active",
        )
    )

    by_level: Dict[int, List[StudentMonthlyEnrollment]] = defaultdict(list)
    for enr in current_enrollments:
        by_level[enr.group.level_id].append(enr)

    created_count = 0
    skipped_count = 0

    for _, enrollments in by_level.items():
        current_level = enrollments[0].group.level
        next_level = get_next_level(current_level)

        if not next_level:
            skipped_count += len(enrollments)
            continue

        mapping = build_next_groups_for_level(
            from_period=from_period,
            to_period=to_period,
            current_level=current_level,
            next_level=next_level,
            enrollments=enrollments,
            created_by=created_by,
        )

        for enr in enrollments:
            target_group = mapping.get(enr.student_id)
            if not target_group:
                skipped_count += 1
                continue

            _, created = StudentMonthlyEnrollment.objects.get_or_create(
                period=to_period,
                student=enr.student,
                group=target_group,
                defaults={
                    "status": "pending",
                    "exam_unlock": False,
                    "source_group": enr.group,  # ✅ très important
                },
            )

            if created:
                created_count += 1
            else:
                skipped_count += 1

    return {
        "created": created_count,
        "skipped": skipped_count,
    }