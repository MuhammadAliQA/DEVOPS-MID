"""Isolated browser-test environment. Never points at the development database."""
import importlib.util
from .settings import *

DEBUG = True
QA_ROOT = Path(os.environ['TICKETFLOW_QA_DIR']).resolve()
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': QA_ROOT / 'qa.sqlite3'}}
MEDIA_ROOT = QA_ROOT / 'uploads'
ALLOWED_HOSTS = ['127.0.0.1', 'localhost', 'testserver']
CSRF_TRUSTED_ORIGINS = ['http://127.0.0.1:8990']
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
TRUST_PROXY_HEADERS = False
AUTH_RATE_LIMIT = 10000
CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
if importlib.util.find_spec('whitenoise') is None:
    MIDDLEWARE = [item for item in MIDDLEWARE if not item.startswith('whitenoise.')]
REST_FRAMEWORK = {**REST_FRAMEWORK, 'DEFAULT_THROTTLE_RATES': {**REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'], 'anon': '10000/min', 'user': '10000/min'}}
