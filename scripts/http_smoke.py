"""Real HTTP customer/staff flow against local disposable demo services.

Use --allow-demo-data explicitly: this creates accounts, events and paid demo tickets.
No payment mocking. QR generation must work for this check to pass.
"""
import argparse
import http.cookiejar
import os
import re
import secrets
import sys
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, Request, build_opener

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--allow-demo-data', action='store_true', required=True)
args = parser.parse_args()
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from django.contrib.auth.models import User, Permission
from django.utils import timezone
from booking.models import Booking, Event, Ticket

BASE = 'http://127.0.0.1:8000'


class Browser:
    def __init__(self):
        self.opener = build_opener(HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def get(self, path):
        with self.opener.open(BASE + path, timeout=10) as response:
            return response.read().decode(), response.url

    def post(self, path, data, form_path=None):
        page, _ = self.get(form_path or path)
        token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', page)
        assert token, f'CSRF input missing: {form_path or path}'
        body = urlencode({**data, 'csrfmiddlewaretoken': token.group(1)}, doseq=True).encode()
        req = Request(BASE + path, body, headers={'Referer': BASE + (form_path or path)})
        with self.opener.open(req, timeout=10) as response:
            return response.read().decode(), response.url


suffix = secrets.token_hex(5)
password = secrets.token_urlsafe(24)
staff = User.objects.create_user('http-operator-' + suffix, password=password, is_staff=True)
staff.user_permissions.set(Permission.objects.filter(content_type__app_label='booking'))
operator = Browser()
operator.post('/accounts/login/', {'username': staff.username, 'password': password})
title = 'HTTP Demo ' + suffix
operator.post('/operations/events/new/', {
    'title': title, 'category': 'music', 'venue': 'HTTP test venue', 'description': 'Disposable demo event',
    'starts_at': (timezone.now() + timedelta(days=2)).isoformat(), 'artwork': 'music',
    'published': 'on', 'refundable': 'on', 'rows': 1, 'seats_per_row': 4,
    'price': 100000, 'vip_price': 200000,
})
event = Event.objects.get(title=title)
assert event.seats.count() == 8
print('PASS: staff login + event/inventory creation over HTTP', flush=True)

customer = Browser()
customer.post('/accounts/register/', {
    'username': 'http-customer-' + suffix, 'password1': password, 'password2': password,
})
listing, _ = customer.get('/?q=' + urlencode({'x': title})[2:])
assert title in listing
seat = event.seats.first()
_, checkout_url = customer.post(f'/events/{event.pk}/book/', {'seats': [seat.pk]}, f'/events/{event.pk}/seats/')
booking_id = checkout_url.rstrip('/').split('/')[-1]
booking = Booking.objects.get(pk=booking_id)
assert booking.status == 'held' and booking.total == 100000
customer.post(f'/bookings/{booking.pk}/', {'contact_name': 'HTTP Customer', 'contact_email': 'smoke@example.com', 'promo_code': 'TICKETLY10'})
booking.refresh_from_db()
assert booking.total == 90000 and booking.discount == 10000
customer.post(f'/bookings/{booking.pk}/pay/', {'outcome': 'decline'}, f'/bookings/{booking.pk}/')
booking.refresh_from_db()
assert booking.status == 'held'
customer.post(f'/bookings/{booking.pk}/pay/', {'outcome': 'approve'}, f'/bookings/{booking.pk}/')
booking.refresh_from_db()
assert booking.status == 'paid'
ticket = Ticket.objects.get(item__booking=booking)
# Retry the same browser POST: no second payment or ticket may appear.
customer.post(f'/bookings/{booking.pk}/pay/', {'outcome': 'approve'}, f'/bookings/{booking.pk}/')
assert Ticket.objects.filter(item__booking=booking).count() == 1
print('PASS: registration + discovery + reservation + decline/retry + actual HTTP payment', flush=True)

calendar, _ = customer.get(f'/bookings/{booking.pk}/calendar/')
assert 'BEGIN:VCALENDAR' in calendar and title in calendar
wallet, _ = customer.get('/tickets/')
assert str(ticket.pk) in wallet
qr_failure = None
try:
    svg, _ = customer.get(f'/tickets/{ticket.pk}/qr/')
    assert '<svg' in svg
    print('PASS: private QR SVG + wallet + calendar', flush=True)
except Exception as exc:
    qr_failure = exc
    print(f'FAIL: QR rendering: {type(exc).__name__}: {exc}', flush=True)

operator.get(f'/staff/scan/{ticket.pk}/')
ticket.refresh_from_db()
assert ticket.checked_in_at is None
operator.post(f'/staff/scan/{ticket.pk}/', {})
ticket.refresh_from_db()
first_scan = ticket.checked_in_at
assert first_scan is not None
operator.post(f'/staff/scan/{ticket.pk}/', {})
ticket.refresh_from_db()
assert ticket.checked_in_at == first_scan
operator.get('/operations/')
operator.get('/operations/bookings/?q=' + suffix)
csv, _ = operator.get('/operations/export/?q=' + suffix)
assert title in csv
print('PASS: staff check-in + duplicate prevention + dashboard + filtered CSV', flush=True)
# Retain payment history but hide synthetic events and disable synthetic accounts.
Event.objects.filter(pk=event.pk).update(published=False)
User.objects.filter(pk__in=[staff.pk, booking.user_id]).update(is_active=False)
if qr_failure:
    raise SystemExit('HTTP scenario incomplete: QR dependency/runtime failure must be resolved.')
print('COMPLETE: real HTTP customer and operations journey passed.')
