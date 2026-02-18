from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from apps.blog.admin import PostAdmin
from apps.blog.models import Post
from richcorp.admin_site import rich_admin_site

# Register your models on your custom admin site
# rich_admin_site.register(Post, PostAdmin)

urlpatterns = [
    path("admin/", admin.site.urls),
    # Register your models on your custom admin site
    # path("admin/", rich_admin_site.urls),
    path("api/v1/", include("apps.blog.urls")),
    path("api/", include("apps.abc_apps.accounts.urls")),
    path("api/academics/", include("apps.abc_apps.academics.urls")),
    path("api/sessions/", include("apps.abc_apps.sessions_abc.urls")),
    path("api/dashboards/", include("apps.abc_apps.dashboards.urls")),
    path("api/teacher/", include("apps.abc_apps.app_teacher.urls")),
    path("", include("apps.abc_apps.students.urls")),
    path("api/", include("apps.abc_apps.attendance.urls")),
    # Frontend website
    path("", include("apps.website.urls")),
]

if settings.DEBUG:
# urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    
    
# ✅ Error handlers (must be module-level)
handler400 = "richcorp.error_views.bad_request"
handler403 = "richcorp.error_views.permission_denied"
handler404 = "richcorp.error_views.page_not_found"
handler500 = "richcorp.error_views.server_error"
