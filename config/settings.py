import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DEBUG = os.getenv('DEBUG', '1') == '1'
SECRET_KEY = os.getenv('SECRET_KEY', 'local-development-only-not-for-production')
PAYMENT_SECRET = os.getenv('PAYMENT_SECRET', 'local-simulator-only')
if not DEBUG and (len(SECRET_KEY) < 50 or len(PAYMENT_SECRET) < 32 or PAYMENT_SECRET == 'local-simulator-only'):
    raise ValueError('Production requires a strong SECRET_KEY and PAYMENT_SECRET')
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1,testserver').split(',')
CSRF_TRUSTED_ORIGINS = [s for s in os.getenv('CSRF_TRUSTED_ORIGINS', '').split(',') if s]
INSTALLED_APPS = [
    'booking.admin_apps.TicketlyAdminConfig', 'django.contrib.auth', 'django.contrib.contenttypes',
    'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles',
    'rest_framework', 'booking',
]
MIDDLEWARE = [
    'config.middleware.RequestContextMiddleware',
    'django.middleware.security.SecurityMiddleware', 'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware', 'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware', 'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware', 'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'config.middleware.AuthRateLimitMiddleware',
]
ROOT_URLCONF = 'config.urls'
TEMPLATES = [{'BACKEND': 'django.template.backends.django.DjangoTemplates',
              'DIRS': [BASE_DIR / 'templates'], 'APP_DIRS': True,
              'OPTIONS': {'context_processors': [
                  'django.template.context_processors.request', 'django.contrib.auth.context_processors.auth',
                  'django.contrib.messages.context_processors.messages']}}]
TEMPLATES[0]['OPTIONS']['context_processors'] += [
    'django.template.context_processors.i18n', 'booking.context_processors.customer_ui']
WSGI_APPLICATION = 'config.wsgi.application'
if os.getenv('DB_HOST'):
    DATABASES = {'default': {'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'ticketflow'), 'USER': os.getenv('DB_USER', 'ticketflow'),
        'PASSWORD': os.environ['DB_PASSWORD'], 'HOST':os.environ['DB_HOST']
	,'PORT': os.getenv('DB_PORT', '5432'),
		'CONN_MAX_AGE': int(os.getenv('DB_CONN_MAX_AGE', '60'))}}
else:
    DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db.sqlite3'}}
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
LANGUAGE_CODE = 'uz'
LANGUAGES = [('uz', 'O‘zbekcha'), ('ru', 'Русский'), ('en', 'English')]
MIDDLEWARE.insert(MIDDLEWARE.index('django.middleware.common.CommonMiddleware'), 'django.middleware.locale.LocaleMiddleware')
LANGUAGE_COOKIE_NAME = 'ticketflow_language'
TIME_ZONE = 'Asia/Tashkent'
USE_I18N = True
USE_TZ = True
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'uploads'
MAX_ACTIVE_HOLDS = 3
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'
PAYMENT_URL = os.getenv('PAYMENT_URL', 'http://127.0.0.1:8001')
QR_BACKEND = os.getenv('QR_BACKEND', 'auto')
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': ['rest_framework_simplejwt.authentication.JWTAuthentication',
                                       'rest_framework.authentication.SessionAuthentication'],
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
    'DEFAULT_THROTTLE_CLASSES': ['rest_framework.throttling.AnonRateThrottle'],
    'DEFAULT_THROTTLE_RATES': {'anon': '60/min'},
}
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', '0') == '1'
TRUST_PROXY_HEADERS = os.getenv('TRUST_PROXY_HEADERS', '0') == '1'
if TRUST_PROXY_HEADERS:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_REDIRECT_EXEMPT = [r'^health/live/$', r'^health/ready/$']
AUTH_RATE_LIMIT = int(os.getenv('AUTH_RATE_LIMIT', '20'))
AUTH_RATE_WINDOW = 60
if os.getenv('REDIS_URL'):
    CACHES = {'default': {'BACKEND': 'django.core.cache.backends.redis.RedisCache', 'LOCATION': os.environ['REDIS_URL']}}
else:
    CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
if not DEBUG and (not os.getenv('DB_HOST') or not os.getenv('REDIS_URL')):
    raise ValueError('Production requires PostgreSQL and Redis')
SECURE_REFERRER_POLICY = 'same-origin'
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.getenv('HSTS_INCLUDE_SUBDOMAINS', '0') == '1'
SECURE_HSTS_PRELOAD = os.getenv('HSTS_PRELOAD', '0') == '1'
LOGGING = {'version': 1, 'disable_existing_loggers': False,
           'formatters': {'json': {'()': 'config.middleware.JsonFormatter'}},
           'handlers': {'console': {'class': 'logging.StreamHandler', 'formatter': 'json'}},
           'root': {'handlers': ['console'], 'level': 'INFO'}}
