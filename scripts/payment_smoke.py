"""Exercise real signed HTTP payment and idempotent ticket creation in CI."""
import os
import sys
import time
from pathlib import Path
from urllib.request import urlopen
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from django.contrib.auth.models import User
from booking.models import Event, Ticket
from booking.services import pay, reserve

for attempt in range(30):
    try:
        with urlopen('http://127.0.0.1:8001/health/live/', timeout=1) as response:
            assert response.status == 200
        break
    except OSError:
        if attempt == 29:
            raise
        time.sleep(.2)
user, _ = User.objects.get_or_create(username='ci-http-smoke')
event = Event.objects.filter(published=True).first()
seat = event.seats.filter(reservation=None).first()
booking = reserve(user, event.pk, [seat.pk])
pay(user, booking.pk)
pay(user, booking.pk)
assert Ticket.objects.filter(item__booking=booking).count() == 1
print('HTTP payment -> exactly one ticket: PASS')
