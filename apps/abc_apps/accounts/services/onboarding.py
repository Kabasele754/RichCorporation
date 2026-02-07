from typing import Optional, Dict, Any
from django.contrib.auth import get_user_model
from django.db import transaction

from apps.abc_apps.accounts.models import (
    StudentProfile,
    TeacherProfile,
    SecretaryProfile,
    PrincipalProfile,
    SecurityProfile,
)

User = get_user_model()


@transaction.atomic
def create_user_with_profile(
    *,
    username: str,
    password: str,
    role: str,
    email: str = "",
    first_name: str = "",
    last_name: str = "",
    code: str = "",
    extra: Optional[Dict[str, Any]] = None,
):
    """
    Creates a user + the correct profile for the role.
    - role: student/teacher/secretary/principal/security
    - code: student_code / teacher_code / etc.
    - extra: extra fields (level/group, speciality, shift/shifts)
    """
    extra = extra or {}

    user = User.objects.create_user(
        username=username,
        password=password,
        email=email,
        first_name=first_name,
        last_name=last_name,
        role=role,
    )

    if role == "student":
        StudentProfile.objects.create(
            user=user,
            student_code=code,
            current_level=extra.get("current_level", "Foundation 1"),
            group_name=extra.get("group_name", "Default Group"),
            status=extra.get("status", "active"),
        )

    elif role == "teacher":
        TeacherProfile.objects.create(
            user=user,
            teacher_code=code,
            speciality=extra.get("speciality", "support"),
        )

    elif role == "secretary":
        SecretaryProfile.objects.create(
            user=user,
            secretary_code=code,
        )

    elif role == "principal":
        PrincipalProfile.objects.create(
            user=user,
            principal_code=code,
        )

    elif role == "security":
        # ✅ support both old field "shift" and new field "shifts"
        shifts = extra.get("shifts")
        shift = extra.get("shift")

        fields = {"user": user, "security_code": code}

        # If model has "shifts" field, use it
        if hasattr(SecurityProfile, "shifts"):
            if shifts is None:
                shifts = [shift or "morning"]
                fields["shifts"] = shifts
        else:
                # fallback old model
                fields["shift"] = shift or "morning"

        SecurityProfile.objects.create(**fields)


    return user
