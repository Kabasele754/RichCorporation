# =========================
# apps/accounts/services/onboarding.py
# =========================
from django.contrib.auth import get_user_model
from apps.abc_apps.accounts.models import StudentProfile, TeacherProfile

User = get_user_model()

def create_student(username: str, password: str, full_name: str, student_code: str, level: str, group_name: str, email: str = ""):
    user = User.objects.create_user(username=username, password=password, email=email, role="student", first_name=full_name)
    profile = StudentProfile.objects.create(user=user, student_code=student_code, current_level=level, group_name=group_name)
    return user, profile

def create_teacher(username: str, password: str, full_name: str, teacher_code: str, speciality: str, email: str = ""):
    user = User.objects.create_user(username=username, password=password, email=email, role="teacher", first_name=full_name)
    profile = TeacherProfile.objects.create(user=user, teacher_code=teacher_code, speciality=speciality)
    return user, profile

def create_secretary(username: str, password: str, full_name: str, email: str = ""):
    user = User.objects.create_user(username=username, password=password, email=email, role="secretary", first_name=full_name)
    return user

def create_principal(username: str, password: str, full_name: str, email: str = ""):
    user = User.objects.create_user(username=username, password=password, email=email, role="principal", first_name=full_name)
    return user
