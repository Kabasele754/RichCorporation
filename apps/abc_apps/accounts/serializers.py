from django.contrib.auth import get_user_model
from rest_framework import serializers
from django.contrib.auth import authenticate
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.abc_apps.accounts.models import (
    StudentProfile,
    TeacherProfile,
    SecretaryProfile,
    PrincipalProfile,
    SecurityProfile,
)
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

User = get_user_model()


# -------------------------
# Base user
# -------------------------
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "role"]


# -------------------------
# Profiles
# -------------------------
class StudentProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = StudentProfile
        fields = [
            "id",
            "user",
            "student_code",
            "current_level",
            "group_name",
            "status",
            "created_at",
            "updated_at",
        ]


class TeacherProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = TeacherProfile
        fields = [
            "id",
            "user",
            "teacher_code",
            "speciality",
            "created_at",
            "updated_at",
        ]


class SecretaryProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = SecretaryProfile
        fields = [
            "id",
            "user",
            "secretary_code",
            "created_at",
            "updated_at",
        ]


class PrincipalProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = PrincipalProfile
        fields = [
            "id",
            "user",
            "principal_code",
            "created_at",
            "updated_at",
        ]


class SecurityProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = SecurityProfile
        fields = [
            "id",
            "user",
            "security_code",
            "shift",
            "created_at",
            "updated_at",
        ]


# -------------------------
# Update student level
# -------------------------
class UpdateStudentLevelSerializer(serializers.Serializer):
    student_id = serializers.IntegerField()
    current_level = serializers.CharField(max_length=50)
    group_name = serializers.CharField(max_length=80)
    status = serializers.ChoiceField(choices=StudentProfile.STATUS_CHOICES, required=False)


# -------------------------
# JWT login serializer
# -------------------------
class AppTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    ✅ Accept username OR email in the 'username' field.
    Example payload:
      { "username": "teacher.grammar", "password": "12345" }
    OR
      { "username": "teacher.grammar@abc.com", "password": "12345" }
    """

    def validate(self, attrs):
        identifier = (attrs.get("username") or "").strip()
        password = attrs.get("password")

        if not identifier or not password:
            raise serializers.ValidationError("username/email and password are required.")

        # ✅ If identifier looks like email → map to real username
        if "@" in identifier:
            user = User.objects.filter(email__iexact=identifier).first()
            if not user:
                raise serializers.ValidationError("No user found with this email.")
            identifier = user.username  # important for authenticate()

        user = authenticate(
            request=self.context.get("request"),
            username=identifier,
            password=password,
        )
        if not user:
            raise serializers.ValidationError("Invalid credentials.")

        # Store for parent class
        self.user = user

        data = super().validate({"username": user.username, "password": password})

        # ✅ Add user payload
        data["user"] = UserSerializer(user).data
        return data

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = getattr(user, "role", "")
        token["username"] = user.username
        token["email"] = user.email
        return token


# -------------------------
# ✅ /auth/me/ serializer
# Always returns:
# { "user": {...}, "profile": {... or null} }
# -------------------------
class MeSerializer(serializers.Serializer):
    user = UserSerializer()
    profile = serializers.DictField(required=False, allow_null=True)

    def to_representation(self, instance):
        u = instance
        role = getattr(u, "role", "student")

        payload = {"user": UserSerializer(u).data, "profile": None}

        if role == "student":
            sp = getattr(u, "student_profile", None)
            payload["profile"] = StudentProfileSerializer(sp).data if sp else None

        elif role == "teacher":
            tp = getattr(u, "teacher_profile", None)
            payload["profile"] = TeacherProfileSerializer(tp).data if tp else None

        elif role == "secretary":
            sec = getattr(u, "secretary_profile", None)
            payload["profile"] = SecretaryProfileSerializer(sec).data if sec else None

        elif role == "principal":
            pr = getattr(u, "principal_profile", None)
            payload["profile"] = PrincipalProfileSerializer(pr).data if pr else None

        elif role == "security":
            sp = getattr(u, "security_profile", None)
            payload["profile"] = SecurityProfileSerializer(sp).data if sp else None

        return payload


from django.contrib.auth.password_validation import validate_password

class MeUpdateSerializer(serializers.Serializer):
    # user fields
    first_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    last_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    email = serializers.EmailField(required=False, allow_blank=True)

    # profile fields (optional, depending role)
    current_level = serializers.CharField(required=False, allow_blank=True, max_length=50)
    group_name = serializers.CharField(required=False, allow_blank=True, max_length=80)
    speciality = serializers.CharField(required=False, allow_blank=True, max_length=12)
    shifts = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )

    def validate_shifts(self, value):
        allowed = {"morning", "afternoon", "night", "full_time"}
        for v in value:
            if v not in allowed:
                raise serializers.ValidationError(f"Invalid shift: {v}")
        return value


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField()
    new_password = serializers.CharField()

    def validate_new_password(self, value):
        validate_password(value)
        return value
    
    
    
class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    default_error_messages = {
        'bad_token': ('Token is expired or invalid')
    }

    def validate(self, attrs):
        self.token = attrs['refresh']
        return attrs

    def save(self, **kwargs):
        try:
            RefreshToken(self.token).blacklist()
        except TokenError:
            self.fail('bad_token')