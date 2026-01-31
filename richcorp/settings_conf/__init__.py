from __future__ import absolute_import, unicode_literals

# Import Celery mais évite le problème d'importation circulaire
try:
    from ..celery import app as celery_app
except ImportError:
    pass

__all__ = ('celery_app',)
