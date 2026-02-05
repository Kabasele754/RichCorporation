# =========================
# apps/accounts/serializers.py
# =========================
from django.contrib.auth import get_user_model
from rest_framework import serializers
from apps.abc_apps.accounts.models import StudentProfile, TeacherProfile

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "role"]

class StudentProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    class Meta:
        model = StudentProfile
        fields = ["id", "user", "student_code", "current_level", "group_name", "status", "created_at", "updated_at"]

class TeacherProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    class Meta:
        model = TeacherProfile
        fields = ["id", "user", "teacher_code", "speciality", "created_at", "updated_at"]

class UpdateStudentLevelSerializer(serializers.Serializer):
    student_id = serializers.IntegerField()
    current_level = serializers.CharField(max_length=50)
    group_name = serializers.CharField(max_length=80)
    status = serializers.ChoiceField(choices=StudentProfile.STATUS_CHOICES, required=False)
