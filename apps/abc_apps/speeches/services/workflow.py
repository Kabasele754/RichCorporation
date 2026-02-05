# =========================
# apps/speeches/services/workflow.py
# =========================
from django.utils import timezone
from apps.abc_apps.speeches.models import Speech, SpeechCorrection, SpeechCoaching, SpeechScore, SpeechPublicationDecision

def submit_speech(speech: Speech):
    speech.status = "submitted"
    speech.submitted_at = timezone.now()
    speech.save(update_fields=["status", "submitted_at"])
    return speech

def apply_correction(speech: Speech, teacher, corrected_content: str, notes: str = ""):
    SpeechCorrection.objects.update_or_create(
        speech=speech,
        defaults={"teacher": teacher, "corrected_content": corrected_content, "correction_notes": notes, "corrected_at": timezone.now()},
    )
    speech.status = "corrected"
    speech.save(update_fields=["status"])
    return speech

def apply_coaching(speech: Speech, teacher, pronunciation_notes: str = ""):
    SpeechCoaching.objects.update_or_create(
        speech=speech,
        defaults={"teacher": teacher, "pronunciation_notes": pronunciation_notes, "coached_at": timezone.now()},
    )
    # if already corrected, move to coached; otherwise keep corrected/submitted progression simple
    speech.status = "coached"
    speech.save(update_fields=["status"])
    return speech

def score_speech(speech: Speech, adjudicator, score: int, comments: str = ""):
    SpeechScore.objects.update_or_create(
        speech=speech,
        adjudicator=adjudicator,
        defaults={"score": score, "comments": comments, "scored_at": timezone.now()},
    )
    return speech

def decide_publication(speech: Speech, decided_by, decision: str, reason: str = ""):
    SpeechPublicationDecision.objects.update_or_create(
        speech=speech,
        defaults={"decided_by": decided_by, "decision": decision, "reason": reason, "decided_at": timezone.now()},
    )
    speech.status = "published" if decision == "publish" else "rejected"
    speech.save(update_fields=["status"])
    return speech
