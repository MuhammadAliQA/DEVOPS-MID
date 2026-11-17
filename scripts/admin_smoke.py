"""Real HTTP/CSRF Django admin CRUD. Requires explicit disposable demo-data flag."""
import argparse
import http.cookiejar
from html.parser import HTMLParser
import os
from pathlib import Path
import secrets
import sys
from datetime import timedelta
from urllib.parse import urlencode
from urllib.request import build_opener, HTTPCookieProcessor, Request

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--allow-demo-data', action='store_true', required=True)
parser.add_argument('--base-url', default='http://127.0.0.1:8000')
args = parser.parse_args()
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from django.contrib.auth.models import User
from django.utils import timezone
from booking.models import Event, AuditLog


class HiddenInputs(HTMLParser):
    def __init__(self, page):
        super().__init__(); self.values = {}; self.feed(page)

    def handle_starttag(self, tag, attrs):
        data = dict(attrs)
        if tag == 'input' and data.get('type') == 'hidden' and data.get('name'):
            self.values[data['name']] = data.get('value', '')


browser = build_opener(HTTPCookieProcessor(http.cookiejar.CookieJar()))
def get(path):
    with browser.open(args.base_url + path, timeout=10) as response:
        return response.read().decode(), response.url

def post(path, data):
    page, _ = get(path)
    hidden = HiddenInputs(page).values
    assert 'csrfmiddlewaretoken' in hidden
    request = Request(args.base_url + path, urlencode({**hidden, **data}).encode(), headers={'Referer': args.base_url + path})
    with browser.open(request, timeout=10) as response:
        return response.read().decode(), response.url


suffix = secrets.token_hex(6)
password = secrets.token_urlsafe(28)
operator = User.objects.create_superuser('admin-smoke-' + suffix, password=password)
event = None
try:
    _, location = post('/admin/login/', {'username': operator.username, 'password': password, 'next': '/admin/'})
    assert location.endswith('/admin/')
    page, _ = get('/admin/')
    assert 'TICKETLY' in page and 'control-metrics' in page
    data = {'title': 'Admin HTTP ' + suffix, 'category': 'music', 'venue': 'Admin test hall', 'city': 'Toshkent',
            'starts_at': (timezone.now() + timedelta(days=4)).isoformat(), 'description': 'Disposable admin smoke event',
            'artwork': 'music', 'published': 'on', 'rows': 2, 'seats_per_row': 3, 'price': 100000, 'vip_price': 200000, '_save': 'Save'}
    _, location = post('/admin/booking/event/add/', data)
    assert location.endswith('/admin/booking/event/')
    event = Event.objects.get(title=data['title'])
    assert event.seats.count() == 12
    assert AuditLog.objects.filter(action='event.created', target=str(event.pk)).exists()
    print('PASS: admin login, dashboard, validated creation, A/VIP inventory and audit', flush=True)
    post(f'/admin/booking/event/{event.pk}/change/', {**data, 'title': data['title'] + ' updated'})
    event.refresh_from_db()
    assert event.title.endswith(' updated') and event.seats.count() == 12
    page, _ = get('/admin/booking/event/?q=' + suffix)
    assert event.title in page
    post(f'/admin/booking/event/{event.pk}/delete/', {'post': 'yes'})
    assert not Event.objects.filter(pk=event.pk).exists()
    print('PASS: admin edit, search and safe deletion over HTTP/CSRF', flush=True)
finally:
    # Only the synthetic account/event from this invocation are touched.
    User.objects.filter(pk=operator.pk).update(is_active=False)
    if event and Event.objects.filter(pk=event.pk).exists() and not event.booking_set.exists():
        event.delete()
