from .base import *

DEBUG = True

ALLOWED_HOSTS = ['95.111.247.13','www.richcorporationsa.com','richcorporationsa.com','api.richcorporationsa.com','localhost']
# Liste des domaines autorisés pour les connexions
CSRF_TRUSTED_ORIGINS = [
    "https://richcorporationsa.com",
    "https://www.richcorporationsa.com",
    'https://api.richcorporationsa.com',
]



# Configuration de la politique de sécurité des contenus (CSP)
CSP_HEADER = {
    'default-src': ["'self'", "richcorporationsa.com"],
    'script-src': ["'self'", "richcorporationsa.com"],
    'style-src': ["'self'", "richcorporationsa.com"],
    'img-src': ["'self'", "richcorporationsa.com"],
    'font-src': ["'self'", "richcorporationsa.com"],
    
}


import os
from pathlib import Path

def read_secret(path, default=""):
    try:
        with open(path, "r") as f:
            return f.read().strip()
    except Exception:
        return default

DB_PASS = os.environ.get("DB_PASS")
DB_PASS_FILE = os.environ.get("DB_PASS_FILE")

if not DB_PASS and DB_PASS_FILE:
    DB_PASS = read_secret(DB_PASS_FILE)

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME", "richcorpdb"),
        "USER": os.environ.get("DB_USER", "richcorpuser"),
        "PASSWORD": DB_PASS or "richcorppass",
        "HOST": os.environ.get("DB_HOST", "db"),
        "PORT": os.environ.get("DB_PORT", "5432"),
    }
}

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': os.environ.get('DB_NAME', 'richcorpdb'),
#         'USER': os.environ.get('DB_USER', 'richcorpuser'),
#         'PASSWORD': os.environ.get('DB_PASS', 'richcorppass'),
#         'HOST': os.environ.get('DB_HOST', 'db'),
#         'PORT': os.environ.get('DB_PORT', '5432'),
#     }
# }

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


# static local this code for to search file css

STATIC_ROOT = "/app/static/"


COMPRESS_ROOT = STATIC_ROOT 


MEDIA_ROOT = '/app/media'




