from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from apps.blog.admin import PostAdmin
from apps.blog.models import Post
from richcorp.admin_site import rich_admin_site

# Register your models on your custom admin site
rich_admin_site.register(Post, PostAdmin)

urlpatterns = [
    # path("admin/", admin.site.urls),
    # Register your models on your custom admin site
    path("admin/", rich_admin_site.urls),
    path("api/v1/", include("apps.blog.urls")),
    
    # Frontend website
    path("", include("apps.website.urls")),
]

if settings.DEBUG:
# urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
