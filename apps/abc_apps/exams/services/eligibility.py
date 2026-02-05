# =========================
# apps/exams/services/eligibility.py
# =========================
from apps.abc_apps.exams.models import ExamRuleStatus

def check_student_eligibility(student_id: int, classroom_id: int):
    rule, _ = ExamRuleStatus.objects.get_or_create(student_id=student_id, classroom_id=classroom_id)
    if rule.eligible:
        return True, ""
    return False, (rule.reason_if_not or "Not eligible")
