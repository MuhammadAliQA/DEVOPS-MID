"""Request correlation and shared-cache authentication burst protection."""
import hashlib
import hmac
import json
import logging
import time
import uuid
from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse

logger = logging.getLogger('ticketly.http')


class JsonFormatter(logging.Formatter):
    def format(self, record):
        result = {'time': self.formatTime(record), 'level': record.levelname, 'logger': record.name, 'message': record.getMessage()}
        for key in ('request_id', 'method', 'route', 'status', 'duration_ms'):
            if hasattr(record, key): result[key] = getattr(record, key)
        if record.exc_info: result['exception'] = self.formatException(record.exc_info)
        return json.dumps(result, ensure_ascii=False)


class RequestContextMiddleware:
    def __init__(self, get_response): self.get_response = get_response

    def __call__(self, request):
        # Generate our own ID: untrusted headers cannot inject log fields.
        request.request_id = uuid.uuid4().hex
        started = time.monotonic()
        response = self.get_response(request)
        response['X-Request-ID'] = request.request_id
        match = getattr(request, 'resolver_match', None)
        logger.info('http_request', extra={'request_id': request.request_id, 'method': request.method,
            'route': getattr(match, 'route', None) or 'unmatched', 'status': response.status_code,
            'duration_ms': round((time.monotonic() - started) * 1000, 2)})
        return response


class AuthRateLimitMiddleware:
    paths = {'/admin/login/', '/accounts/login/', '/accounts/register/', '/accounts/password/change/', '/api/token/', '/api/token/refresh/', '/api/register/'}

    def __init__(self, get_response): self.get_response = get_response

    def __call__(self, request):
        if request.method != 'POST' or request.path not in self.paths:
            return self.get_response(request)
        # Production Caddy replaces X-Real-IP, and the app port is private.
        ip = request.META.get('HTTP_X_REAL_IP', '') if settings.TRUST_PROXY_HEADERS else request.META.get('REMOTE_ADDR', '')
        identity = hmac.new(settings.SECRET_KEY.encode(), ip.encode(), hashlib.sha256).hexdigest()
        window = settings.AUTH_RATE_WINDOW
        bucket = int(time.time()) // window
        key = f'auth:{identity}:{bucket}'
        try:
            if cache.add(key, 1, timeout=window + 1):
                count = 1
            else:
                count = cache.incr(key)
        except Exception:
            logger.exception('auth_rate_store_unavailable')
            return JsonResponse({'code': 'auth_temporarily_unavailable'}, status=503)
        if count > settings.AUTH_RATE_LIMIT:
            response = JsonResponse({'code': 'auth_rate_limited', 'detail': 'Too many attempts. Please wait and retry.'}, status=429)
            response['Retry-After'] = str(window - int(time.time()) % window)
            return response
        return self.get_response(request)
