from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.utils.text import slugify
from parler.utils.context import switch_language

from apps.blog.models import Post, PostCategory


class Command(BaseCommand):
    help = "Manage blog posts (create/list/publish/unpublish/delete/seed) with FR/EN translations."

    def add_arguments(self, parser):
        parser.add_argument(
            "action",
            choices=["create", "list", "publish", "unpublish", "delete", "seed"],
            help="Action to perform: create | list | publish | unpublish | delete | seed",
        )

        # Common filters
        parser.add_argument("--lang", default="fr", choices=["fr", "en"], help="Language context for translated fields.")
        parser.add_argument("--slug", default=None, help="Post slug (for publish/unpublish/delete).")
        parser.add_argument("--id", type=int, default=None, help="Post id (for publish/unpublish/delete).")

        # Create args
        parser.add_argument("--category", default=PostCategory.UNIVERSITY, choices=[c for c, _ in PostCategory.choices])
        parser.add_argument("--title", default=None, help="Post title (translated field).")
        parser.add_argument("--excerpt", default="", help="Post excerpt (translated field).")
        parser.add_argument("--content", default="", help="Post content (translated field).")
        parser.add_argument("--published", action="store_true", help="Mark as published.")
        parser.add_argument("--published-at", default=None, help="Publish date ISO (e.g. 2026-01-18T10:00:00).")

        # Seed args
        parser.add_argument("--count", type=int, default=6, help="Number of demo posts to generate for seed action.")

        # List args
        parser.add_argument("--all", action="store_true", help="List all posts (including unpublished).")
        parser.add_argument("--category-filter", default=None, choices=[c for c, _ in PostCategory.choices], help="Filter list by category.")
        parser.add_argument("--contains", default=None, help="Filter list: title contains text (case-insensitive).")

    def handle(self, *args, **opts):
        action = opts["action"]
        lang = opts["lang"]

        if action == "create":
            return self._create(opts, lang)
        if action == "list":
            return self._list(opts, lang)
        if action == "publish":
            return self._set_publish(opts, True)
        if action == "unpublish":
            return self._set_publish(opts, False)
        if action == "delete":
            return self._delete(opts)
        if action == "seed":
            return self._seed(opts)

        raise CommandError("Unknown action")

    # ---------- Helpers ----------
    def _get_post(self, opts) -> Post:
        post_id = opts.get("id")
        slug = opts.get("slug")

        if post_id:
            try:
                return Post.objects.get(id=post_id)
            except Post.DoesNotExist:
                raise CommandError(f"Post with id={post_id} not found.")

        if slug:
            try:
                return Post.objects.get(slug=slug)
            except Post.DoesNotExist:
                raise CommandError(f"Post with slug='{slug}' not found.")

        raise CommandError("Provide --id or --slug.")

    def _create(self, opts, lang: str):
        title = opts.get("title")
        if not title:
            raise CommandError("Missing --title for create action.")

        category = opts.get("category", PostCategory.UNIVERSITY)
        excerpt = opts.get("excerpt", "")
        content = opts.get("content", "")

        published = bool(opts.get("published"))
        published_at_raw = opts.get("published_at")

        if published_at_raw:
            try:
                published_at = timezone.datetime.fromisoformat(published_at_raw)
                if timezone.is_naive(published_at):
                    published_at = timezone.make_aware(published_at, timezone.get_current_timezone())
            except Exception:
                raise CommandError("Invalid --published-at. Use ISO: 2026-01-18T10:00:00")
        else:
            published_at = timezone.now()

        # slug unique
        base_slug = slugify(title)[:210] or "post"
        slug = base_slug
        i = 2
        while Post.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{i}"
            i += 1

        post = Post(
            category=category,
            slug=slug,
            published=published,
            published_at=published_at,
        )
        post.save()

        # Set translated fields in given lang
        with switch_language(post, lang):
            post.title = title
            post.excerpt = excerpt
            post.content = content
            post.save()

        self.stdout.write(self.style.SUCCESS(f"✅ Created post: id={post.id} slug='{post.slug}' lang={lang} published={post.published}"))
        return

    def _list(self, opts, lang: str):
        qs = Post.objects.all().order_by("-published_at")
        if not opts.get("all"):
            qs = qs.filter(published=True)
        if opts.get("category_filter"):
            qs = qs.filter(category=opts["category_filter"])

        contains = opts.get("contains")
        if contains:
            # Search in translated title fields (works with Parler, best-effort)
            qs = qs.filter(translations__title__icontains=contains)

        if not qs.exists():
            self.stdout.write("No posts found.")
            return

        self.stdout.write(self.style.MIGRATE_HEADING("Blog posts:"))
        for p in qs[:200]:
            with switch_language(p, lang):
                t = getattr(p, "title", "") or p.safe_translation_getter("title", any_language=True) or ""
            self.stdout.write(
                f"- id={p.id} | slug={p.slug} | category={p.category} | published={p.published} | date={p.published_at:%Y-%m-%d} | title[{lang}]={t[:60]!r}"
            )

    def _set_publish(self, opts, value: bool):
        post = self._get_post(opts)
        post.published = value
        if value and not post.published_at:
            post.published_at = timezone.now()
        post.save(update_fields=["published", "published_at", "updated_at"])
        state = "published ✅" if value else "unpublished ⛔"
        self.stdout.write(self.style.SUCCESS(f"Post {post.id} ({post.slug}) is now {state}"))

    def _delete(self, opts):
        post = self._get_post(opts)
        pid, slug = post.id, post.slug
        post.delete()
        self.stdout.write(self.style.WARNING(f"🗑 Deleted post id={pid} slug='{slug}'"))

    def _seed(self, opts):
        """
        Create demo posts in FR, and (optionally) EN will be auto-filled by your signals
        if GOOGLE_TRANSLATE_ENABLED=1.
        """
        n = max(1, int(opts.get("count", 6)))
        now = timezone.now()

        demos = [
            (PostCategory.UNIVERSITY, "Dates d’inscription — Universités SA", "Calendrier et deadlines importantes.", "Mise à jour : vérifiez les dates d’inscription et les documents requis."),
            (PostCategory.VISA, "Visa étudiant : checklist VFS", "Documents essentiels pour votre dossier.", "Passeport, lettre d’admission, preuve financière, assurance…"),
            (PostCategory.HOUSING, "Logement : comment choisir en sécurité", "Critères pour éviter les mauvaises surprises.", "Proximité campus, sécurité, contrat, état des lieux…"),
            (PostCategory.INSURANCE, "Assurance médicale : ce qui est exigé", "Couvertures compatibles pour l’immigration.", "Nous vous aidons à sélectionner la meilleure option."),
        ]

        created = 0
        for i in range(n):
            cat, title, excerpt, content = demos[i % len(demos)]
            title_i = f"{title} (#{i+1})"
            base_slug = slugify(title_i)[:210] or "post"
            slug = base_slug
            k = 2
            while Post.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{k}"
                k += 1

            p = Post(
                category=cat,
                slug=slug,
                published=True,
                published_at=now - timezone.timedelta(days=i),
            )
            p.save()
            with switch_language(p, "fr"):
                p.title = title_i
                p.excerpt = excerpt
                p.content = content
                p.save()
            created += 1

        self.stdout.write(self.style.SUCCESS(f"✅ Seed done. Created {created} posts."))
