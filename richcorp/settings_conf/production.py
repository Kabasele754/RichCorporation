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

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'richcorpdb'),
        'USER': os.environ.get('DB_USER', 'richcorpuser'),
        'PASSWORD': os.environ.get('DB_PASS', 'richcorppass'),
        'HOST': os.environ.get('DB_HOST', 'db'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}


# static local this code for to search file css

STATIC_ROOT = "/app/static/"


COMPRESS_ROOT = STATIC_ROOT 


MEDIA_ROOT = '/app/media'




