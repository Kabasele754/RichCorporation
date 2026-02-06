from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/



# SECURITY WARNING: don't run with debug turned on in production!

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-secret-change-me")
DEBUG = os.getenv("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")


# Application definition

INSTALLED_APPS = [
    "django_extensions",
    "apps.abc_apps.accounts",
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "parler",
    "django_celery_beat",

    "apps.common",
    "apps.blog",
    "apps.website",
    
    # ABC Apps
    # "apps.abc_apps.commons",
    "apps.abc_apps.academics",
    "apps.abc_apps.sessions_abc",
    "apps.abc_apps.attendance",
    "apps.abc_apps.exams",
    "apps.abc_apps.feedback",
    "apps.abc_apps.news",
    "apps.abc_apps.speeches",
    "apps.abc_apps.gate_security.apps.GateSecurityConfig",
    "apps.abc_apps.access_control.apps.AccessControlConfig",
    "apps.abc_apps.library.apps.LibraryConfig",
    "apps.abc_apps.dashboards.apps.DashboardsConfig",
    
    
    
]

MIDDLEWARE = [
     "corsheaders.middleware.CorsMiddleware",
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    # i18n
    "django.middleware.locale.LocaleMiddleware",
    
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'richcorp.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR/'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]


WSGI_APPLICATION = 'richcorp.wsgi.application'
ASGI_APPLICATION = 'richcorp.asgi.application'


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases





# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

AUTH_USER_MODEL = "accounts.User"


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = "fr"
LANGUAGES = (("fr", "French"), ("en", "English"))
TIME_ZONE = "Africa/Johannesburg"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

# STATICFILES_DIRS = [
#     os.path.join(BASE_DIR, "static"),
# ]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# CORS
CORS_ALLOW_ALL_ORIGINS = DEBUG
if not DEBUG:
    CORS_ALLOWED_ORIGINS = [o.strip() for o in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",") if o.strip()]
CORS_ALLOW_CREDENTIALS = True

# DRF
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",
        "rest_framework.parsers.FormParser",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 3,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
}

# Parler translations (models fields translated)
PARLER_LANGUAGES = {
    None: ({"code": "fr"}, {"code": "en"}),
    "default": {"fallbacks": ["fr"], "hide_untranslated": False},
}

# Redis cache

# Google Translate (optional)
GOOGLE_TRANSLATE_ENABLED = os.getenv("GOOGLE_TRANSLATE_ENABLED", "0") == "1"
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "")



# Configuration de Celery
CELERY_ENABLE_UTC = True
CELERY_TIMEZONE = 'UTC' 
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_BROKER_URL = 'redis://redis:6379'  # URL de connexion à Redis pour la file d'attente des tâches
CELERY_RESULT_BACKEND = 'redis://redis:6379'  # URL de connexion à Redis pour stocker les résultats des tâches
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True


# channel layer redis work on mac and docker
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [('redis', 6379)],
        },
    },
}

from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    # every day at 18:00 local time
    "library_reading_reminders_daily": {
        "task": "apps.abc_apps.library.tasks.send_reading_reminders_task",
        "schedule": crontab(hour=18, minute=0),
    },

    # return reminders every 10 minutes
    "library_return_reminders_every_10min": {
        "task": "apps.abc_apps.library.tasks.send_return_reminders_task",
        "schedule": crontab(minute="*/10"),
    },
}