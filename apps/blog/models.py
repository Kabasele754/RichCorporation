from django.db import models
from django.utils.text import slugify
from django.utils import timezone
from parler.models import TranslatableModel, TranslatedFields

from apps.common.models import TimeStampedModel
from apps.common.utils_images import make_webp, make_thumb_webp

class PostCategory(models.TextChoices):
    UNIVERSITY = "university", "University"
    VISA = "visa", "Visa"
    HOUSING = "housing", "Housing"
    INSURANCE = "insurance", "Insurance"

class Post(TimeStampedModel, TranslatableModel):
    category = models.CharField(max_length=24, choices=PostCategory.choices, default=PostCategory.UNIVERSITY)

    slug = models.SlugField(max_length=220, unique=True, db_index=True)

    # Original uploaded image
    cover_image = models.ImageField(upload_to="blog/covers/", blank=True, null=True)

    # Optimized outputs (generated automatically)
    cover_webp = models.ImageField(upload_to="blog/covers_webp/", blank=True, null=True, editable=False)
    cover_thumb_webp = models.ImageField(upload_to="blog/covers_thumb_webp/", blank=True, null=True, editable=False)

    published = models.BooleanField(default=True, db_index=True)
    published_at = models.DateTimeField(default=timezone.now, db_index=True)
    
    source_hash_fr = models.CharField(max_length=64, blank=True, default="")
    source_hash_en = models.CharField(max_length=64, blank=True, default="")

    translations = TranslatedFields(
        title=models.CharField(max_length=220),
        excerpt=models.CharField(max_length=280, blank=True, default=""),
        content=models.TextField(blank=True, default=""),
    )

    class Meta:
        ordering = ["-published_at"]
        indexes = [
            models.Index(fields=["published", "published_at"]),
            models.Index(fields=["category", "published_at"]),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            title_any = self.safe_translation_getter("title", any_language=True) or "post"
            self.slug = slugify(title_any)[:210]

        # Generate optimized images when cover_image present
        if self.cover_image:
            try:
                base_name = (self.slug or "cover").replace("/", "-")
                # WebP main
                webp_file = make_webp(self.cover_image)
                self.cover_webp.save(f"{base_name}.webp", webp_file, save=False)
                # WebP thumb
                thumb_file = make_thumb_webp(self.cover_image)
                self.cover_thumb_webp.save(f"{base_name}_thumb.webp", thumb_file, save=False)
            except Exception:
                # Keep original upload, do not break save
                pass

        super().save(*args, **kwargs)

    def __str__(self):
        return self.safe_translation_getter("title", any_language=True) or self.slug
