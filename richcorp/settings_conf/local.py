from .base import *

DEBUG = True

ALLOWED_HOSTS = ['*']


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


# DATABASES = {
#     "default": {
#         "ENGINE": os.getenv("DB_ENGINE", "django.db.backends.sqlite3"),
#         "NAME": os.getenv("DB_NAME", str(BASE_DIR / "db.sqlite3")),
#         "USER": os.getenv("DB_USER", ""),
#         "PASSWORD": os.getenv("DB_PASSWORD", ""),
#         "HOST": os.getenv("DB_HOST", ""),
#         "PORT": os.getenv("DB_PORT", ""),
#     }
# }


# DATABASES = {
#     'default': {
#         'ENGINE': 'django_tenants.postgresql_backend',
#         'NAME': os.environ.get('DB_NAME', 'visodb'),
#         'USER': os.environ.get('DB_USER', 'trustmeuser'),
#         'PASSWORD': os.environ.get('DB_PASS', 'trustmepass'),
#         'HOST': os.environ.get('DB_HOST', 'db'),
#         'PORT': os.environ.get('DB_PORT', '5432'),
#     }
# }


# local static
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

# local media
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')