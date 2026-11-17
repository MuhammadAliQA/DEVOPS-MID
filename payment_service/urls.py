import hashlib
import hmac
import json
import uuid
from django.conf import settings
from django.http import JsonResponse
from django.urls import path
from django.views.decorators.http import require_POST


@require_POST
def charge(request):
    if len(request.body) > 4096:
        return JsonResponse({'error': 'too_large'}, status=413)
    expected = hmac.new(settings.SECRET_KEY.encode(), request.body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, request.headers.get('X-Signature', '')):
        return JsonResponse({'error': 'unauthorized'}, status=403)
    try:
        data = json.loads(request.body)
        booking_id = str(uuid.UUID(data['booking']))
        amount = data['amount']
        if type(amount) is not int or amount <= 0 or data['currency'] != 'UZS' or data['outcome'] not in ('approve', 'decline'):
            raise ValueError()
    except (ValueError, KeyError, TypeError, AttributeError):
        return JsonResponse({'error': 'invalid_payload'}, status=400)
    # No money is moved. A deterministic reference makes retries safe without a ledger.
    reference = hashlib.sha256(f'demo:{booking_id}:{amount}:UZS'.encode()).hexdigest()
    return JsonResponse({'status': 'approved' if data['outcome'] == 'approve' else 'declined',
                         'reference': reference, 'simulated': True})


urlpatterns = [path('charge/', charge), path('health/live/', lambda r: JsonResponse({'status': 'ok', 'service': 'payment-simulator'}))]
