import os
import signal
import logging
from pathlib import Path
from threading import Event
from django.db import close_old_connections, OperationalError
from django.core.management.base import BaseCommand
from django.utils import timezone
from booking.models import Booking
from booking.services import expire_event


class Command(BaseCommand):
    help = 'Release expired reservations; --loop runs every 15 seconds.'

    def add_arguments(self, parser):
        parser.add_argument('--loop', action='store_true')

    def handle(self, *args, **options):
        stop = Event()
        previous = {}
        if options['loop']:
            for sig in (signal.SIGTERM, signal.SIGINT):
                previous[sig] = signal.signal(sig, lambda *_: stop.set())
        try:
            while not stop.is_set():
                close_old_connections()
                try:
                    ids = list(Booking.objects.filter(status='held', expires_at__lte=timezone.now()).order_by().values_list('event_id', flat=True).distinct())
                    for event_id in ids:
                        expire_event(event_id)
                    if ids:
                        self.stdout.write(f'Expiry sweep: {len(ids)} events')
                    if os.getenv('EXPIRY_HEARTBEAT'):
                        Path(os.environ['EXPIRY_HEARTBEAT']).touch()
                except OperationalError:
                    logging.getLogger('ticketly.worker').exception('expiry_database_unavailable')
                    if not options['loop']: raise
                if not options['loop']: return
                stop.wait(15)
        finally:
            for sig, handler in previous.items(): signal.signal(sig, handler)
