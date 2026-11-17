import hashlib
import importlib.util
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from unittest import skipUnless
from unittest.mock import patch

from django.contrib.auth.models import User, Permission
from django.db import close_old_connections, connection, connections
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from .models import Booking, Event, Payment, Seat, Ticket
from .services import BookingError, cancel, check_in, expire_event, pay, reserve
from .qr import available as qr_available, opencv_svg


def inventory():
    event = Event.objects.create(title='Test concert', category='music', venue='Tashkent',
                                 starts_at=timezone.now() + timedelta(days=5), published=True)
    seats = [Seat.objects.create(event=event, row='A', number=i, price=100000) for i in range(1, 4)]
    return event, seats


class BookingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('customer', password='Example-strong-2048')
        self.other = User.objects.create_user('other', password='Example-strong-2048')
        self.event, self.seats = inventory()

    def hold(self):
        return reserve(self.user, self.event.pk, [self.seats[0].pk])

    def test_hold_prices_come_from_inventory_and_expire_in_ten_minutes(self):
        booking = self.hold()
        self.assertEqual(booking.total, 100000)
        self.assertAlmostEqual((booking.expires_at - timezone.now()).total_seconds(), 600, delta=2)
        self.seats[0].refresh_from_db()
        self.assertEqual(self.seats[0].reservation_id, booking.pk)

    def test_double_booking_rejected(self):
        self.hold()
        with self.assertRaises(BookingError):
            reserve(self.other, self.event.pk, [self.seats[0].pk])
        self.assertEqual(Booking.objects.count(), 1)

    def test_duplicate_empty_and_too_many_seats_rejected(self):
        for ids in ([], [self.seats[0].pk] * 2, list(range(9))):
            with self.assertRaises(BookingError):
                reserve(self.user, self.event.pk, ids)

    def test_cross_event_seats_rejected(self):
        other, seats = inventory()
        with self.assertRaises(BookingError):
            reserve(self.user, self.event.pk, [seats[0].pk])

    def test_unpublished_and_past_events_rejected(self):
        self.event.published = False
        self.event.save()
        with self.assertRaises(BookingError):
            self.hold()
        self.event.published = True
        self.event.starts_at = timezone.now() - timedelta(hours=1)
        self.event.save()
        with self.assertRaises(BookingError):
            self.hold()

    def test_expiry_releases_inventory_but_retains_history(self):
        booking = self.hold()
        Booking.objects.filter(pk=booking.pk).update(expires_at=timezone.now() - timedelta(seconds=1))
        expire_event(self.event.pk)
        booking.refresh_from_db()
        self.seats[0].refresh_from_db()
        self.assertEqual(booking.status, 'expired')
        self.assertIsNone(self.seats[0].reservation_id)
        self.assertEqual(booking.items.count(), 1)
        new = reserve(self.other, self.event.pk, [self.seats[0].pk])
        self.assertNotEqual(new.pk, booking.pk)

    def test_cancel_and_ownership(self):
        booking = self.hold()
        with self.assertRaises(Booking.DoesNotExist):
            cancel(self.other, booking.pk)
        cancel(self.user, booking.pk)
        self.seats[0].refresh_from_db()
        self.assertIsNone(self.seats[0].reservation_id)

    @patch('booking.services.simulate_payment', return_value='demo-reference')
    def test_payment_idempotent_and_ticket_not_reissued(self, charge):
        booking = self.hold()
        pay(self.user, booking.pk)
        pay(self.user, booking.pk)
        self.assertEqual(Payment.objects.count(), 1)
        self.assertEqual(Ticket.objects.count(), 1)
        charge.assert_called_once()
        with self.assertRaises(BookingError):
            cancel(self.user, booking.pk)

    @patch('booking.services.simulate_payment', side_effect=BookingError('declined'))
    def test_decline_does_not_issue_ticket_or_release_active_hold(self, charge):
        booking = self.hold()
        with self.assertRaises(BookingError):
            pay(self.user, booking.pk)
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'held')
        self.assertFalse(Ticket.objects.exists())
        self.assertFalse(Payment.objects.exists())

    @patch('booking.services.simulate_payment')
    def test_expired_booking_cannot_pay(self, charge):
        booking = self.hold()
        Booking.objects.filter(pk=booking.pk).update(expires_at=timezone.now() - timedelta(seconds=1))
        with self.assertRaises(BookingError):
            pay(self.user, booking.pk)
        charge.assert_not_called()

    def test_expiry_during_remote_payment_does_not_issue_ticket(self):
        booking = self.hold()
        def slow_charge(*args):
            Booking.objects.filter(pk=booking.pk).update(expires_at=timezone.now() - timedelta(seconds=1))
            return 'late'
        with patch('booking.services.simulate_payment', side_effect=slow_charge):
            with self.assertRaises(BookingError):
                pay(self.user, booking.pk)
        self.assertFalse(Ticket.objects.exists())

    @patch('booking.services.simulate_payment', return_value='demo-reference')
    def test_duplicate_check_in_rejected(self, charge):
        booking = self.hold()
        pay(self.user, booking.pk)
        ticket = Ticket.objects.get()
        check_in(ticket.pk)
        with self.assertRaises(BookingError):
            check_in(ticket.pk)


class WebTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('customer', password='Example-strong-2048')
        self.staff = User.objects.create_user('operator', password='Example-strong-2048', is_staff=True)
        self.staff.user_permissions.set(Permission.objects.filter(content_type__app_label='booking'))
        self.event, self.seats = inventory()

    def test_catalog_detail_login_register_and_health_render(self):
        for url in ['/', f'/events/{self.event.pk}/', '/accounts/login/', '/accounts/register/', '/health/live/', '/health/ready/']:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_invalid_filters_render_validation_instead_of_error(self):
        self.assertContains(self.client.get('/?max_price=no&date=invalid'), 'errorlist')

    def test_operations_require_staff(self):
        self.client.force_login(self.user)
        for url in ['/operations/', '/operations/events/', '/operations/bookings/', '/operations/export/', '/operations/gate/']:
            self.assertEqual(self.client.get(url).status_code, 403)

    def test_operations_pages_render(self):
        self.client.force_login(self.staff)
        for url in ['/operations/', '/operations/events/', '/operations/events/new/', f'/operations/events/{self.event.pk}/', '/operations/bookings/', '/operations/gate/']:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_staff_can_create_inventory_and_edit_event(self):
        self.client.force_login(self.staff)
        values = {'title': 'New event', 'category': 'sport', 'venue': 'Stadium', 'description': 'Demo',
                  'starts_at': (timezone.now() + timedelta(days=10)).isoformat(), 'artwork': 'sport',
                  'rows': 2, 'seats_per_row': 4, 'price': 50000, 'vip_price': 90000, 'published': 'on'}
        self.assertEqual(self.client.post('/operations/events/new/', values).status_code, 302)
        event = Event.objects.get(title='New event')
        self.assertEqual(event.seats.count(), 16)
        values['title'] = 'Updated'
        self.assertEqual(self.client.post(f'/operations/events/{event.pk}/', values).status_code, 302)
        self.assertEqual(event.seats.count(), 16)

    def test_staff_delete_requires_post_and_preserves_booking_history(self):
        self.client.force_login(self.staff)
        url = reverse('ops-event-delete', args=[self.event.pk])
        self.assertEqual(self.client.get(url).status_code, 405)
        reserve(self.user, self.event.pk, [self.seats[0].pk])
        self.assertEqual(self.client.post(url).status_code, 302)
        self.assertTrue(Event.objects.filter(pk=self.event.pk).exists())
        empty_event, seats = inventory()
        self.client.post(reverse('ops-event-delete', args=[empty_event.pk]))
        self.assertFalse(Event.objects.filter(pk=empty_event.pk).exists())
        self.assertFalse(Seat.objects.filter(pk__in=[seat.pk for seat in seats]).exists())

    def test_post_requires_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        response = client.post(f'/events/{self.event.pk}/book/', {'seats': [self.seats[0].pk]})
        self.assertEqual(response.status_code, 403)

    @patch('booking.services.simulate_payment', return_value='demo-reference')
    def test_checkout_wallet_calendar_and_authorization(self, charge):
        self.client.force_login(self.user)
        response = self.client.post(f'/events/{self.event.pk}/book/', {'seats': [self.seats[0].pk]})
        self.assertEqual(response.status_code, 302)
        booking = Booking.objects.get()
        self.assertEqual(self.client.get(response.url).status_code, 200)
        self.assertEqual(self.client.post(f'/bookings/{booking.pk}/pay/').status_code, 302)
        self.assertContains(self.client.get('/tickets/'), 'QR chipta')
        self.assertContains(self.client.get(f'/bookings/{booking.pk}/calendar/'), 'BEGIN:VCALENDAR')
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(f'/bookings/{booking.pk}/').status_code, 404)
        self.assertEqual(self.client.get(reverse('qr', args=[Ticket.objects.get().pk])).status_code, 404)

    @skipUnless(qr_available(), 'No QR backend installed')
    @patch('booking.services.simulate_payment', return_value='demo-reference')
    def test_qr_svg(self, charge):
        self.client.force_login(self.user)
        booking = reserve(self.user, self.event.pk, [self.seats[0].pk])
        pay(self.user, booking.pk)
        response = self.client.get(reverse('qr', args=[Ticket.objects.get().pk]))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'<svg', response.content)

    @skipUnless(importlib.util.find_spec('cv2'), 'Optional OpenCV backend not installed')
    def test_optional_qr_backend_decodes_to_exact_scan_url(self):
        import cv2
        import numpy as np
        import re
        import xml.etree.ElementTree as ET
        url = 'http://localhost:8000/staff/scan/12345678-1234-1234-1234-123456789abc/'
        root = ET.fromstring(opencv_svg(url))
        size = int(root.attrib['viewBox'].split()[-1])
        bitmap = np.full((size, size), 255, dtype=np.uint8)
        path = root.find('{http://www.w3.org/2000/svg}path').attrib['d']
        for x, y in re.findall(r'M(\d+),(\d+)h1v1h-1z', path):
            bitmap[int(y), int(x)] = 0
        enlarged = cv2.resize(bitmap, None, fx=8, fy=8, interpolation=cv2.INTER_NEAREST)
        decoded, _, _ = cv2.QRCodeDetector().detectAndDecode(enlarged)
        self.assertEqual(decoded, url)

    def test_export_escapes_spreadsheet_formulas(self):
        self.user.username = '=1+1'
        self.user.save()
        reserve(self.user, self.event.pk, [self.seats[0].pk])
        self.client.force_login(self.staff)
        self.assertContains(self.client.get('/operations/export/'), "'=1+1")

    def test_jwt_registration_login_and_booking(self):
        response = self.client.post('/api/register/', {'username': 'api-user', 'password1': 'Example-strong-2048', 'password2': 'Example-strong-2048'})
        self.assertEqual(response.status_code, 201)
        token = self.client.post('/api/token/', {'username': 'api-user', 'password': 'Example-strong-2048'}).json()['access']
        response = self.client.post('/api/bookings/', {'event': self.event.pk, 'seats': [self.seats[0].pk]}, content_type='application/json', HTTP_AUTHORIZATION='Bearer ' + token)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['total'], 100000)

    def test_api_seat_availability_and_booking_owner(self):
        booking = reserve(self.user, self.event.pk, [self.seats[0].pk])
        seats = self.client.get(f'/api/events/{self.event.pk}/seats/').json()
        self.assertFalse(seats[0]['available'])
        self.assertTrue(seats[1]['available'])
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(f'/api/bookings/{booking.pk}/').status_code, 200)
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(f'/api/bookings/{booking.pk}/').status_code, 404)

    @patch('booking.services.simulate_payment', return_value='demo-reference')
    def test_scan_is_staff_only_and_get_never_consumes_ticket(self, charge):
        booking = reserve(self.user, self.event.pk, [self.seats[0].pk])
        pay(self.user, booking.pk)
        ticket = Ticket.objects.get()
        url = reverse('scan', args=[ticket.pk])
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(url).status_code, 200)
        ticket.refresh_from_db()
        self.assertIsNone(ticket.checked_in_at)
        self.assertEqual(self.client.post(url).status_code, 200)
        ticket.refresh_from_db()
        first_scan = ticket.checked_in_at
        self.assertIsNotNone(first_scan)
        self.client.post(url)
        ticket.refresh_from_db()
        self.assertEqual(ticket.checked_in_at, first_scan)


@skipUnless(connection.vendor == 'postgresql', 'PostgreSQL required to verify row locks')
class ConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.event, self.seats = inventory()
        self.users = [User.objects.create_user(f'user{i}') for i in range(2)]

    def test_parallel_reservations_have_exactly_one_winner(self):
        barrier = threading.Barrier(2)
        def attempt(user_id):
            close_old_connections()
            try:
                user = User.objects.get(pk=user_id)
                barrier.wait(timeout=10)
                reserve(user, self.event.pk, [self.seats[0].pk])
                return 'reserved'
            except BookingError:
                return 'unavailable'
            finally:
                # Persistent, healthy connections survive close_old_connections().
                # Each worker owns thread-local connections: close them before the
                # thread exits so PostgreSQL can drop the test database afterwards.
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(attempt, [u.pk for u in self.users]))
        self.assertCountEqual(results, ['reserved', 'unavailable'])
        self.assertEqual(Booking.objects.count(), 1)
