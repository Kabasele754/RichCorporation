from .base import *

DEBUG = True

ALLOWED_HOSTS = ['66.94.124.105','www.richcorporations.com','richcorporations.com','api.richcorporations.com','localhost']
# Liste des domaines autorisés pour les connexions
CSRF_TRUSTED_ORIGINS = [
    "https://richcorporations.com",
    "https://www.richcorporations.com",
    'https://api.richcorporations.com',
]



# Configuration de la politique de sécurité des contenus (CSP)
CSP_HEADER = {
    'default-src': ["'self'", "richcorporations.com"],
    'script-src': ["'self'", "richcorporations.com"],
    'style-src': ["'self'", "richcorporations.com"],
    'img-src': ["'self'", "richcorporations.com"],
    'font-src': ["'self'", "richcorporations.com"],
    
}

DATABASES = {
    'default': {
        'ENGINE': 'django_tenants.postgresql_backend',
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




