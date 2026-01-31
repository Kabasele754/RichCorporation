from django.db.models.signals import post_save
from django.dispatch import receiver
from parler.utils.context import switch_language
from apps.blog.models import Post
from apps.blog.services_translate import translate_text

@receiver(post_save, sender=Post)
def auto_translate_post(sender, instance: Post, created, **kwargs):
    # We translate only when one language exists and the other is missing
    # Keep it safe: never overwrite existing translations.
    # Languages: fr <-> en
    langs = ["fr", "en"]

    # try to get any language title
    title_any = instance.safe_translation_getter("title", any_language=True)
    if not title_any:
        return

    for src in langs:
        dst = "en" if src == "fr" else "fr"
        with switch_language(instance, src):
            src_title = instance.title if hasattr(instance, "title") else ""
            src_excerpt = getattr(instance, "excerpt", "") or ""
            src_content = getattr(instance, "content", "") or ""

        with switch_language(instance, dst):
            dst_title = getattr(instance, "title", "") or ""
            dst_excerpt = getattr(instance, "excerpt", "") or ""
            dst_content = getattr(instance, "content", "") or ""

            if not dst_title and src_title:
                t_title = translate_text(src_title, src, dst)
                if t_title:
                    instance.title = t_title

            if not dst_excerpt and src_excerpt:
                t_excerpt = translate_text(src_excerpt, src, dst)
                if t_excerpt:
                    instance.excerpt = t_excerpt

            if not dst_content and src_content:
                t_content = translate_text(src_content, src, dst)
                if t_content:
                    instance.content = t_content

            # Only save if something was filled
            if (not dst_title and getattr(instance, "title", "")) or (not dst_excerpt and getattr(instance, "excerpt", "")) or (not dst_content and getattr(instance, "content", "")):
                instance.save(update_fields=[])  # parler handles translation save
