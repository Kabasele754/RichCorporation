# =========================
# apps/academics/serializers.py
# =========================
from rest_framework import serializers
from apps.abc_apps.academics.models import ClassRoom, Course, TeacherCourseAssignment, MonthlyGoal

class ClassRoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClassRoom
        fields = "__all__"

class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = "__all__"

class TeacherCourseAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeacherCourseAssignment
        fields = "__all__"

class MonthlyGoalSerializer(serializers.ModelSerializer):
    class Meta:
        model = MonthlyGoal
        fields = "__all__"
