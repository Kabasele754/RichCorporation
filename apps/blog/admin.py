from django.contrib import admin
from django.utils.html import format_html
from django.conf import settings
from parler.admin import TranslatableAdmin
from parler.utils.context import switch_language
import hashlib

from apps.blog.models import Post
from apps.blog.services_translate import translate_text

def _hash_payload(title: str, excerpt: str, content: str) -> str:
    raw = f"{title}\n{excerpt}\n{content}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

# @admin.register(Post)
class PostAdmin(TranslatableAdmin):
    list_display = ("slug", "category", "published", "published_at", "cover_preview")
    list_filter = ("category", "published")
    search_fields = ("translations__title", "translations__excerpt", "slug")
    ordering = ("-published_at",)
    date_hierarchy = "published_at"
    readonly_fields = ("cover_preview_large", "cover_webp", "cover_thumb_webp")

    fieldsets = (
        ("Publication", {"fields": ("published", "published_at", "category", "slug")}),
        ("Image", {"fields": ("cover_image", "cover_preview_large", "cover_webp", "cover_thumb_webp")}),
        ("Contenu (traduit)", {"fields": ("title", "excerpt", "content")}),
    )

    # ---------- PREVIEWS ----------
    def cover_preview(self, obj):
        if obj.cover_thumb_webp:
            return format_html(
                '<img src="{}" style="height:36px;border-radius:10px;border:1px solid #ddd;" />',
                obj.cover_thumb_webp.url
            )
        if obj.cover_image:
            return format_html(
                '<img src="{}" style="height:36px;border-radius:10px;border:1px solid #ddd;" />',
                obj.cover_image.url
            )
        return "-"
    cover_preview.short_description = "Cover"

    def cover_preview_large(self, obj):
        if obj.cover_webp:
            return format_html(
                '<img src="{}" style="max-height:220px;border-radius:16px;border:1px solid #ddd;" />',
                obj.cover_webp.url
            )
        if obj.cover_image:
            return format_html(
                '<img src="{}" style="max-height:220px;border-radius:16px;border:1px solid #ddd;" />',
                obj.cover_image.url
            )
        return "—"
    cover_preview_large.short_description = "Preview"

    # ---------- AUTO-TRANSLATE ON SAVE ----------
    def save_model(self, request, obj, form, change):
        # 1) Save ce que l’admin vient d’éditer (FR ou EN)
        super().save_model(request, obj, form, change)

        # 2) Si translate désactivé → stop
        if not getattr(settings, "GOOGLE_TRANSLATE_ENABLED", False):
            return

        # 3) La langue active Parler est dans ?language=fr|en
        src = (request.GET.get("language") or request.POST.get("language") or "fr").lower()
        src = "en" if src.startswith("en") else "fr"
        dst = "en" if src == "fr" else "fr"

        # 4) Lire la version source STRICTEMENT
        with switch_language(obj, src):
            src_title = (getattr(obj, "title", "") or "").strip()
            src_excerpt = (getattr(obj, "excerpt", "") or "").strip()
            src_content = (getattr(obj, "content", "") or "").strip()

        if not (src_title or src_excerpt or src_content):
            return

        # 5) Calculer l’empreinte (hash) du contenu source
        new_hash = _hash_payload(src_title, src_excerpt, src_content)

        # 6) Comparer à l’ancien hash stocké
        hash_field = "source_hash_fr" if src == "fr" else "source_hash_en"
        old_hash = (getattr(obj, hash_field, "") or "").strip()

        # Si rien n’a changé depuis la dernière traduction → ne rien faire
        if old_hash == new_hash:
            return

        # 7) Traduire (mise à jour automatique du dst)
        t_title = translate_text(src_title, src, dst) if src_title else ""
        t_excerpt = translate_text(src_excerpt, src, dst) if src_excerpt else ""
        t_content = translate_text(src_content, src, dst) if src_content else ""

        # 8) Écrire la traduction destination (force-create)
        obj.set_current_language(dst)
        if t_title:
            obj.title = t_title
        if t_excerpt:
            obj.excerpt = t_excerpt
        if t_content:
            obj.content = t_content
        obj.save()

        # 9) Mettre à jour le hash (pour éviter retraductions inutiles)
        setattr(obj, hash_field, new_hash)
        obj.save(update_fields=[hash_field])