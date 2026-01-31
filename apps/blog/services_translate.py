from django.conf import settings

def translate_text(text: str, source_lang: str, target_lang: str) -> str:
    """
    Robust:
    - if disabled: returns ""
    - if errors: returns ""
    """
    if not text or not text.strip():
        return ""
    if not settings.GOOGLE_TRANSLATE_ENABLED:
        return ""

    try:
        # Google Cloud Translate v3
        from google.cloud import translate
        client = translate.TranslationServiceClient()
        parent = f"projects/{settings.GOOGLE_CLOUD_PROJECT}/locations/global"

        resp = client.translate_text(
            request={
                "parent": parent,
                "contents": [text],
                "mime_type": "text/plain",
                "source_language_code": source_lang,
                "target_language_code": target_lang,
            }
        )
        if resp.translations:
            return resp.translations[0].translated_text or ""
        return ""
    except Exception:
        return ""
