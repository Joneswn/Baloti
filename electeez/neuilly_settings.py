from django.utils.translation import gettext_lazy as _

from .settings import *

SITE_ID = 2
SITE_NAME = 'neuilly'

LANGUAGE_CODE = 'fr'

LANGUAGES = (
    ('fr', _('French')),
    ('en', _('English')),
)


STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'public'
STATICFILES_DIRS = [
    BASE_DIR / 'static' / SITE_NAME,
    BASE_DIR / 'static',
]

if DEBUG:
    STATIC_URL = f'/static/{SITE_NAME}/'
    STATIC_ROOT = BASE_DIR / 'public' / SITE_NAME