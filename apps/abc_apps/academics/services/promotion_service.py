from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from django.db import transaction
from django.db.models import Count

from apps.abc_apps.academics.models import (
    AcademicLevel,
    AcademicPeriod,
    MonthlyClassGroup,
    Room,
    StudentMonthlyEnrollment,
)


MAX_STUDENTS_PER_GROUP = 25


def get_next_level(level: AcademicLevel) -> Optional[AcademicLevel]:
    return (
        AcademicLevel.objects
        .filter(order__gt=level.order)
        .order_by("order")
        .first()
    )


def group_letter_from_index(i: int) -> str:
    """
    0 -> A
    1 -> B
    2 -> C
    ...
    25 -> Z
    26 -> A2
    27 -> B2
    """
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    if i < 26:
        return letters[i]
    return f"{letters[i % 26]}{(i // 26) + 1}"


def get_available_rooms_for_level(level: AcademicLevel) -> List[Room]:
    """
    Tu peux améliorer cette logique plus tard:
    - filtrer par campus
    - filtrer par capacité >= 25
    - filtrer par building/floor
    Pour l’instant on prend les rooms actives.
    """
    return list(
        Room.objects
        .filter(is_active=True)
        .order_by("code")
    )


def choose_room_for_group(
    used_room_ids: set,
    candidate_rooms: List[Room],
) -> Optional[Room]:
    for room in candidate_rooms:
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


def build_next_month_groups_for_level(
    *,
    from_period: AcademicPeriod,
    to_period: AcademicPeriod,
    current_level: AcademicLevel,
    next_level: AcademicLevel,
    student_ids: List[int],
    created_by=None,
) -> Dict[int, MonthlyClassGroup]:
    """
    Retourne un mapping:
    student_id -> MonthlyClassGroup du mois suivant

    Logique:
    - on regarde l'ancien groupe des étudiants
    - on essaye de garder les cohortes ensemble
    - max 25 students par groupe
    - on crée automatiquement les MonthlyClassGroup
    """

    # enrollments actifs du mois courant pour ces students
    current_enrollments = list(
        StudentMonthlyEnrollment.objects
        .select_related("group", "group__level", "group__room")
        .filter(
            period=from_period,
            student_id__in=student_ids,
            status="active",
            group__level=current_level,
        )
    )

    # regroupe les étudiants par ancien group_name
    old_group_buckets: Dict[str, List[StudentMonthlyEnrollment]] = defaultdict(list)
    for enr in current_enrollments:
        old_group_buckets[enr.group.group_name].append(enr)

    # pour stabilité, on traite A puis B puis C...
    ordered_old_groups = sorted(old_group_buckets.keys())

    candidate_rooms = get_available_rooms_for_level(next_level)
    used_room_ids = set()

    result: Dict[int, MonthlyClassGroup] = {}
    next_group_index = 0

    for old_group_name in ordered_old_groups:
        enrollments = old_group_buckets[old_group_name]

        # on coupe en paquets de 25
        for i in range(0, len(enrollments), MAX_STUDENTS_PER_GROUP):
            chunk = enrollments[i:i + MAX_STUDENTS_PER_GROUP]

            new_group_name = group_letter_from_index(next_group_index)
            next_group_index += 1

            room = choose_room_for_group(used_room_ids, candidate_rooms)
            if not room:
                raise ValueError(
                    f"No available room found to create group {next_level.label} {new_group_name}"
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
def promote_students_to_next_period(
    *,
    from_period: AcademicPeriod,
    to_period: AcademicPeriod,
    student_ids: List[int],
    created_by=None,
) -> Dict[str, int]:
    """
    Promotion intelligente:
    - retrouve le next level
    - construit les groupes du mois suivant
    - crée les StudentMonthlyEnrollment

    Retourne un résumé.
    """

    # récupère les enrollments actifs
    enrollments = list(
        StudentMonthlyEnrollment.objects
        .select_related("group", "group__level")
        .filter(
            period=from_period,
            student_id__in=student_ids,
            status="active",
        )
    )

    # bucket par level actuel
    by_level: Dict[int, List[StudentMonthlyEnrollment]] = defaultdict(list)
    for enr in enrollments:
        by_level[enr.group.level_id].append(enr)

    created_count = 0
    skipped_count = 0

    for level_id, level_enrollments in by_level.items():
        current_level = level_enrollments[0].group.level
        next_level = get_next_level(current_level)

        if not next_level:
            # dernier niveau, on ignore ou on garde selon ta logique
            skipped_count += len(level_enrollments)
            continue

        level_student_ids = [x.student_id for x in level_enrollments]

        mapping = build_next_month_groups_for_level(
            from_period=from_period,
            to_period=to_period,
            current_level=current_level,
            next_level=next_level,
            student_ids=level_student_ids,
            created_by=created_by,
        )

        for enr in level_enrollments:
            target_group = mapping.get(enr.student_id)
            if not target_group:
                skipped_count += 1
                continue

            _, created = StudentMonthlyEnrollment.objects.get_or_create(
                period=to_period,
                student_id=enr.student_id,
                group=target_group,
                defaults={
                    "status": "pending",
                    "exam_unlock": False,
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