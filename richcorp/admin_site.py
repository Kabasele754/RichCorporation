from django.contrib.admin import AdminSite

from apps.blog.admin import PostAdmin
from apps.blog.models import Post

class RichAdminSite(AdminSite):
    site_header = "Rich Corporation — Admin"
    site_title = "Rich Corporation"
    index_title = "Administration"

rich_admin_site = RichAdminSite(name="rich_admin")

# rich_admin_site.register(Post, PostAdmin)