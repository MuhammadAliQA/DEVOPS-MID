import io
import uuid
from datetime import timedelta
from unittest.mock import patch
from PIL import Image
from django.contrib.auth.models import Group, Permission, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.conf import settings
from django.utils import timezone
from .forms import EventForm
from .models import AuditLog, Booking, PaymentAttempt, Seat, Ticket
from .services import BookingError, cancel, pay, reserve
from .tests import inventory


class ReliabilityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('reliability-customer')
        self.event, self.seats = inventory()

    def test_same_key_returns_same_booking_without_reallocating(self):
        key = uuid.uuid4()
        first = reserve(self.user, self.event.pk, [self.seats[0].pk], key)
        second = reserve(self.user, self.event.pk, [self.seats[0].pk], key)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(Booking.objects.count(), 1)
        self.assertEqual(AuditLog.objects.filter(action='booking.reserved').count(), 1)

    def test_key_cannot_be_reused_for_different_seats(self):
        key = uuid.uuid4()
        reserve(self.user, self.event.pk, [self.seats[0].pk], key)
        with self.assertRaises(BookingError) as caught:
            reserve(self.user, self.event.pk, [self.seats[1].pk], key)
        self.assertEqual(caught.exception.code, 'idempotency_conflict')

    def test_cancelled_key_does_not_create_another_booking(self):
        key = uuid.uuid4()
        first = reserve(self.user, self.event.pk, [self.seats[0].pk], key)
        cancel(self.user, first.pk)
        result = reserve(self.user, self.event.pk, [self.seats[0].pk], key)
        self.assertEqual(result.status, 'cancelled')
        self.assertEqual(Booking.objects.count(), 1)

    def test_key_is_scoped_to_customer(self):
        key = uuid.uuid4()
        other = User.objects.create_user('other-reliability')
        reserve(self.user, self.event.pk, [self.seats[0].pk], key)
        reserve(other, self.event.pk, [self.seats[1].pk], key)
        self.assertEqual(Booking.objects.count(), 2)

    def test_expired_key_returns_expired_state_and_releases_inventory(self):
        key = uuid.uuid4()
        first = reserve(self.user, self.event.pk, [self.seats[0].pk], key)
        Booking.objects.filter(pk=first.pk).update(expires_at=timezone.now() - timedelta(seconds=1))
        replay = reserve(self.user, self.event.pk, [self.seats[0].pk], key)
        self.assertEqual(replay.status, 'expired')
        self.assertIsNone(Seat.objects.get(pk=self.seats[0].pk).reservation_id)

    @patch('booking.services.simulate_payment')
    def test_payment_attempt_burst_is_rejected_before_remote_call(self, charge):
        booking = reserve(self.user, self.event.pk, [self.seats[0].pk])
        PaymentAttempt.objects.bulk_create([PaymentAttempt(booking=booking, status='failed') for _ in range(10)])
        with self.assertRaises(BookingError) as caught:
            pay(self.user, booking.pk)
        self.assertEqual(caught.exception.code, 'payment_rate_limited')
        charge.assert_not_called()

    def test_invalid_key_and_hold_limit(self):
        with self.assertRaises(BookingError):
            reserve(self.user, self.event.pk, [self.seats[0].pk], 'invalid')
        for seat in self.seats:
            reserve(self.user, self.event.pk, [seat.pk])
        extra = Seat.objects.create(event=self.event, row='A', number=4, price=100000)
        with self.assertRaises(BookingError) as caught:
            reserve(self.user, self.event.pk, [extra.pk])
        self.assertEqual(caught.exception.code, 'hold_limit')

    @patch('booking.services.simulate_payment', side_effect=BookingError('declined', 'payment_declined'))
    def test_failed_attempt_is_durable(self, simulate):
        booking = reserve(self.user, self.event.pk, [self.seats[0].pk])
        with self.assertRaises(BookingError):
            pay(self.user, booking.pk)
        attempt = PaymentAttempt.objects.get()
        self.assertEqual((attempt.status, attempt.error_code), ('failed', 'payment_declined'))
        self.assertIsNotNone(attempt.finished_at)
        self.assertTrue(AuditLog.objects.filter(action='payment.failed', actor=self.user).exists())

    def test_late_approval_persists_abandoned_attempt(self):
        booking = reserve(self.user, self.event.pk, [self.seats[0].pk])
        def charge(*args):
            Booking.objects.filter(pk=booking.pk).update(expires_at=timezone.now() - timedelta(seconds=1))
            return 'late-approval'
        with patch('booking.services.simulate_payment', side_effect=charge):
            with self.assertRaises(BookingError):
                pay(self.user, booking.pk)
        self.assertEqual(PaymentAttempt.objects.get().status, 'abandoned')
        self.assertFalse(Ticket.objects.exists())

    def test_operator_cancel_records_operator_not_customer(self):
        staff = User.objects.create_user('audit-operator', is_staff=True)
        booking = reserve(self.user, self.event.pk, [self.seats[0].pk])
        cancel(self.user, booking.pk, actor=staff)
        self.assertEqual(AuditLog.objects.get(action='booking.cancelled').actor, staff)

    def test_api_idempotency_header(self):
        self.client.force_login(self.user)
        payload = {'event': self.event.pk, 'seats': [self.seats[0].pk]}
        headers = {'HTTP_IDEMPOTENCY_KEY': str(uuid.uuid4())}
        first = self.client.post('/api/bookings/', payload, content_type='application/json', **headers)
        second = self.client.post('/api/bookings/', payload, content_type='application/json', **headers)
        self.assertEqual(first.status_code, 201)
        self.assertEqual(first.json()['id'], second.json()['id'])

    def test_favorites_preserve_local_filter_but_reject_external_redirect(self):
        self.client.force_login(self.user)
        response = self.client.post(f'/events/{self.event.pk}/favorite/', {'next': '/?category=music'})
        self.assertEqual(response.url, '/?category=music')
        response = self.client.post(f'/events/{self.event.pk}/favorite/', {'next': 'https://example.org/'})
        self.assertEqual(response.url, '/')


class PermissionAndUploadTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user('limited-staff', is_staff=True)
        self.client.force_login(self.staff)
        self.event, self.seats = inventory()

    def test_staff_flag_alone_grants_no_operations_access(self):
        for url in ['/operations/', '/operations/events/', '/operations/bookings/', '/operations/gate/', '/operations/activity/', '/operations/payments/']:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)

    def test_gate_role_cannot_read_revenue_or_edit_events(self):
        call_command('setup_roles', verbosity=0)
        self.staff.groups.add(Group.objects.get(name='Gate staff'))
        self.assertEqual(self.client.get('/operations/gate/').status_code, 200)
        self.assertEqual(self.client.get('/operations/').status_code, 403)
        self.assertEqual(self.client.get('/operations/events/new/').status_code, 403)

    def test_auditor_sees_audit_not_payment_attempts(self):
        self.staff.user_permissions.add(Permission.objects.get(content_type__app_label='booking', codename='view_auditlog'))
        self.assertEqual(self.client.get('/operations/activity/').status_code, 200)
        self.assertEqual(self.client.get('/operations/payments/').status_code, 403)

    def test_booking_reader_cannot_see_revenue_dashboard(self):
        self.staff.user_permissions.add(Permission.objects.get(content_type__app_label='booking', codename='view_booking'))
        self.assertEqual(self.client.get('/operations/bookings/').status_code, 200)
        self.assertEqual(self.client.get('/operations/').status_code, 403)

    def data(self):
        return {'title': 'Poster test', 'category': 'music', 'venue': 'Venue', 'description': 'Description',
                'starts_at': (timezone.now() + timedelta(days=2)).isoformat(), 'artwork': 'music'}

    def test_real_png_accepted_and_svg_rejected(self):
        stream = io.BytesIO()
        Image.new('RGB', (20, 20), 'blue').save(stream, format='PNG')
        form = EventForm(self.data(), {'poster': SimpleUploadedFile('poster.png', stream.getvalue(), content_type='image/png')}, instance=self.event)
        self.assertTrue(form.is_valid(), form.errors)
        form = EventForm(self.data(), {'poster': SimpleUploadedFile('poster.svg', b'<svg onload="alert(1)"/>', content_type='image/svg+xml')}, instance=self.event)
        self.assertFalse(form.is_valid())

    def test_poster_serves_with_debug_disabled_and_hides_drafts(self):
        stream = io.BytesIO()
        Image.new('RGB', (20, 20), 'blue').save(stream, format='PNG')
        with override_settings(MEDIA_ROOT=settings.BASE_DIR / '.tmp' / 'poster-tests', DEBUG=False):
            self.event.poster.save('test-' + uuid.uuid4().hex + '.png', SimpleUploadedFile('poster.png', stream.getvalue()))
            try:
                response = self.client.get(f'/events/{self.event.pk}/poster/')
                self.assertEqual(response.status_code, 200)
                self.assertTrue(b''.join(response.streaming_content).startswith(b'\x89PNG'))
                response.close()
                self.event.published = False
                self.event.save()
                self.assertEqual(self.client.get(f'/events/{self.event.pk}/poster/').status_code, 404)
            finally:
                self.event.poster.delete()
