from django.db import models
from django.conf import settings
from django.db.models import Q

# ✅ Import tes models existants (adapte le chemin)
from apps.abc_apps.academics.models import (
    AcademicPeriod,
    MonthlyClassGroup,
    TeacherProfile,
    StudentProfile,
    Course,
)

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class WeeklyTeachingPlan(TimeStampedModel):
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, related_name="weekly_plans")
    period = models.ForeignKey(AcademicPeriod, on_delete=models.CASCADE, related_name="weekly_plans")
    monthly_group = models.ForeignKey(MonthlyClassGroup, on_delete=models.CASCADE, related_name="weekly_plans")
    course = models.ForeignKey(Course, on_delete=models.PROTECT, related_name="weekly_plans")

    week_start = models.DateField()  # Monday

    monday = models.TextField(blank=True, default="")
    tuesday = models.TextField(blank=True, default="")
    wednesday = models.TextField(blank=True, default="")
    thursday = models.TextField(blank=True, default="")
    friday = models.TextField(blank=True, default="")
    saturday = models.TextField(blank=True, default="")
    sunday = models.TextField(blank=True, default="")

    class Meta:
        unique_together = ("teacher", "monthly_group", "course", "week_start")
        indexes = [
            models.Index(fields=["teacher", "period"]),
            models.Index(fields=["monthly_group", "week_start"]),
        ]

    def __str__(self):
        return f"{self.teacher} - {self.course} - {self.week_start}"


class Homework(TimeStampedModel):
    STATUS_CHOICES = [("draft", "Draft"), ("published", "Published"), ("archived", "Archived")]

    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, related_name="homeworks")
    period = models.ForeignKey(AcademicPeriod, on_delete=models.CASCADE, related_name="homeworks")
    group = models.ForeignKey(MonthlyClassGroup, on_delete=models.CASCADE, related_name="homeworks")
    course = models.ForeignKey(Course, on_delete=models.PROTECT, related_name="homeworks")

    title = models.CharField(max_length=160)
    instructions = models.TextField(blank=True, default="")
    book_pages = models.CharField(max_length=120, blank=True, default="")  # ex: "p. 12–15"
    resources = models.JSONField(default=list, blank=True)  # [{type,url,name}, ...]

    due_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="published")

    class Meta:
        indexes = [
            models.Index(fields=["period", "group"]),
            models.Index(fields=["teacher", "period"]),
            models.Index(fields=["course", "due_date"]),
        ]

    def __str__(self):
        return f"{self.title} - {self.group} - {self.course}"


class HomeworkSubmission(TimeStampedModel):
    STATUS_CHOICES = [("submitted", "Submitted"), ("late", "Late"), ("graded", "Graded")]

    homework = models.ForeignKey(Homework, on_delete=models.CASCADE, related_name="submissions")
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="homework_submissions")

    content = models.TextField(blank=True, default="")
    attachments = models.JSONField(default=list, blank=True)

    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="submitted")

    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    teacher_comment = models.TextField(blank=True, default="")

    class Meta:
        unique_together = ("homework", "student")
        indexes = [
            models.Index(fields=["student"]),
            models.Index(fields=["homework"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.homework_id} - {self.student_id}"


class StudentProofScan(models.Model):
    PURPOSE_CHOICES = [
        ("book_completed", "Book completed"),
        ("exam_eligible", "Exam eligible"),
        ("attendance_proof", "Attendance proof"),
        ("other", "Other"),
    ]

    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, related_name="proof_scans")
    period = models.ForeignKey(AcademicPeriod, on_delete=models.CASCADE, related_name="proof_scans")
    group = models.ForeignKey(MonthlyClassGroup, on_delete=models.CASCADE, related_name="proof_scans")

    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="proof_scans")
    course = models.ForeignKey(Course, on_delete=models.PROTECT, null=True, blank=True, related_name="proof_scans")

    purpose = models.CharField(max_length=30, choices=PURPOSE_CHOICES)
    note = models.TextField(blank=True, default="")
    meta = models.JSONField(default=dict, blank=True)  # ex: {"unit":"Unit 3", "pages":"12-20"}

    scanned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["period", "group"]),
            models.Index(fields=["student", "period"]),
            models.Index(fields=["teacher", "period"]),
        ]
        # ✅ règle anti-doublon (course peut être NULL)
        constraints = [
            models.UniqueConstraint(
                fields=["period", "student", "course", "purpose", "group"],
                name="uniq_proofscan_period_student_course_purpose",
            )
        ]

    def __str__(self):
        return f"{self.student_id} {self.purpose} {self.scanned_at}"


class StudentRemark(models.Model):
    AREA_CHOICES = [
        ("pronunciation", "Pronunciation"),
        ("vocabulary", "Vocabulary"),
        ("grammar", "Grammar"),
        ("fluency", "Fluency"),
        ("listening", "Listening"),
        ("writing", "Writing"),
        ("behavior", "Behavior"),
        ("other", "Other"),
    ]
    SEVERITY_CHOICES = [("low", "Low"), ("medium", "Medium"), ("high", "High")]

    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, related_name="teacher_student_remarks")

    period = models.ForeignKey(AcademicPeriod, on_delete=models.CASCADE, related_name="student_remarks")
    group = models.ForeignKey(MonthlyClassGroup, on_delete=models.CASCADE, related_name="student_remarks")
    student = models.ForeignKey(
    StudentProfile,
    on_delete=models.CASCADE,
    related_name="teacher_student_remarks",   # ✅ unique
    related_query_name="teacher_student_remark"
)

    course = models.ForeignKey(Course, on_delete=models.PROTECT, null=True, blank=True, related_name="student_remarks")

    area = models.CharField(max_length=20, choices=AREA_CHOICES)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default="medium")

    title = models.CharField(max_length=160, blank=True, default="")
    observation = models.TextField()              # ce que tu observes
    recommendation = models.TextField(blank=True, default="")  # comment s'améliorer
    target_for_next = models.TextField(blank=True, default="") # objectif perso (optionnel)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["student", "period"]),
            models.Index(fields=["group", "period"]),
            models.Index(fields=["area"]),
        ]


class StudentMonthlyObjective(models.Model):
    """
    ✅ Objectifs “mois prochain” écrits par le teacher titulaire (ou autorisé)
    """
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, related_name="monthly_objectives")
    period = models.ForeignKey(AcademicPeriod, on_delete=models.CASCADE, related_name="monthly_objectives")
    group = models.ForeignKey(MonthlyClassGroup, on_delete=models.CASCADE, related_name="monthly_objectives")
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="monthly_objectives")

    objectives = models.JSONField(default=dict, blank=True)
    # ex:
    # {
    #   "pronunciation": "Work on /th/ and stress",
    #   "vocabulary": "Learn 50 words from Unit 4",
    #   "grammar": "Master present perfect"
    # }

    teacher_description = models.TextField(blank=True, default="")  # description/encouragement pour aider
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("period", "group", "student")  # 1 fiche / mois / student / classe
        indexes = [
            models.Index(fields=["student", "period"]),
            models.Index(fields=["group", "period"]),
        ]


class ClassGeneralRemark(models.Model):
    """
    ✅ remarque sur la classe + solutions proposées
    """
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, related_name="class_remarks")
    period = models.ForeignKey(AcademicPeriod, on_delete=models.CASCADE, related_name="class_remarks")
    group = models.ForeignKey(MonthlyClassGroup, on_delete=models.CASCADE, related_name="class_remarks")

    title = models.CharField(max_length=160)
    observation = models.TextField()            # problème général
    proposed_solutions = models.TextField()     # solutions proposées
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["group", "period"]),
            models.Index(fields=["teacher", "period"]),
        ]
