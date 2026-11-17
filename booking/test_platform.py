from datetime import timedelta
from unittest.mock import patch
from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.utils import timezone
from .models import Event, Seat, Booking, PaymentAttempt
from .services import BookingError, reserve, pay


class PlatformTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user('platform', password='Test-platform-2339')
        self.event = Event.objects.create(title='Starts soon', category='music', venue='Test', published=True,
            starts_at=timezone.now() + timedelta(minutes=2))
        self.seat = Seat.objects.create(event=self.event, row='A', number=1, price=100000)

    def tearDown(self): cache.clear()

    def test_hold_never_outlives_event_start(self):
        booking = reserve(self.user, self.event.pk, [self.seat.pk])
        self.assertEqual(booking.expires_at, self.event.starts_at)

    @patch('booking.services.simulate_payment', return_value='test-ref')
    def test_unpublished_event_cannot_start_payment(self, simulate):
        booking = reserve(self.user, self.event.pk, [self.seat.pk])
        Event.objects.filter(pk=self.event.pk).update(published=False)
        with self.assertRaises(BookingError): pay(self.user, booking.pk)
        simulate.assert_not_called()

    @patch('booking.services.simulate_payment')
    def test_event_closed_during_payment_does_not_issue_ticket(self, simulate):
        booking = reserve(self.user, self.event.pk, [self.seat.pk])
        def close(*_):
            Event.objects.filter(pk=self.event.pk).update(starts_at=timezone.now() - timedelta(seconds=1))
            return 'test-ref'
        simulate.side_effect = close
        with self.assertRaises(BookingError): pay(self.user, booking.pk)
        self.assertFalse(booking.items.filter(ticket__isnull=False).exists())
        self.assertEqual(PaymentAttempt.objects.get(booking=booking).status, 'abandoned')

    @override_settings(AUTH_RATE_LIMIT=2)
    def test_auth_limit_shared_across_paths_and_clients_but_not_ips(self):
        for _ in range(2): self.client.post('/api/token/', {'username': 'bad', 'password': 'bad'})
        response = Client().post('/accounts/login/', {'username': 'bad', 'password': 'bad'})
        self.assertEqual(response.status_code, 429)
        self.assertGreater(int(response['Retry-After']), 0)
        self.assertNotEqual(self.client.post('/api/token/', {}, REMOTE_ADDR='192.0.2.4').status_code, 429)
        self.assertEqual(self.client.get('/health/live/').status_code, 200)

    @override_settings(AUTH_RATE_LIMIT=1, TRUST_PROXY_HEADERS=False)
    def test_untrusted_ip_header_cannot_bypass_limit(self):
        self.client.post('/api/token/', {}, HTTP_X_REAL_IP='192.0.2.1')
        self.assertEqual(self.client.post('/api/token/', {}, HTTP_X_REAL_IP='192.0.2.2').status_code, 429)

    def test_request_correlation_and_cache_outage(self):
        response = self.client.get('/health/live/', HTTP_X_REQUEST_ID='untrusted-header')
        self.assertEqual(len(response['X-Request-ID']), 32)
        self.assertNotEqual(response['X-Request-ID'], 'untrusted-header')
        with patch('config.middleware.cache.add', side_effect=ConnectionError('offline')):
            self.assertEqual(self.client.post('/api/token/', {}).status_code, 503)
        with patch('django.core.cache.cache.set', side_effect=ConnectionError('offline')):
            self.assertEqual(self.client.get('/health/ready/').status_code, 503)

    def test_api_checkout_and_cancel_use_owner_and_server_price(self):
        booking = reserve(self.user, self.event.pk, [self.seat.pk])
        self.client.force_login(self.user)
        url = f'/api/bookings/{booking.pk}/'
        response = self.client.post(url + 'checkout/', {'contact_name': 'API Customer', 'contact_email': 'api@example.com', 'promo_code': 'TICKETLY10', 'total': 1})
        self.assertEqual(response.json()['total'], 90000)
        other = User.objects.create_user('other-platform')
        self.client.force_login(other)
        self.assertEqual(self.client.post(url + 'cancel/').status_code, 404)
        self.client.force_login(self.user)
        self.assertEqual(self.client.post(url + 'cancel/').status_code, 200)
        self.seat.refresh_from_db()
        self.assertIsNone(self.seat.reservation_id)
