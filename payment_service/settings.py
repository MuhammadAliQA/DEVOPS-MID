import os

DEBUG = os.getenv('DEBUG', '1') == '1'
SECRET_KEY = os.getenv('PAYMENT_SECRET', 'local-simulator-only')
if not DEBUG and (SECRET_KEY == 'local-simulator-only' or len(SECRET_KEY) < 32):
    raise ValueError('Set PAYMENT_SECRET')
ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'payment', 'testserver']
ROOT_URLCONF = 'payment_service.urls'
INSTALLED_APPS = []
MIDDLEWARE = ['django.middleware.security.SecurityMiddleware']
DATA_UPLOAD_MAX_MEMORY_SIZE = 4096
