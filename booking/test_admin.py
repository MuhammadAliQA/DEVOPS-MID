from datetime import timedelta
from unittest.mock import patch
from django.contrib.auth.models import User, Permission
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from .models import AuditLog, Event, Seat, Booking, Payment
from .services import reserve, pay


class ControlAdminTests(TestCase):
    def setUp(self):
        cache.clear()
        self.admin = User.objects.create_superuser('control-admin', password='Control-strong-4427')
        self.customer = User.objects.create_user('customer-control')
        self.client.force_login(self.admin)
        self.event = Event.objects.create(title='Control Event', category='music', venue='Control Hall',
            starts_at=timezone.now() + timedelta(days=5), published=True)
        self.seat = Seat.objects.create(event=self.event, row='A', number=1, price=120000)

    def tearDown(self): cache.clear()

    def data(self, **kwargs):
        return {'title': 'Created by admin', 'category': 'music', 'venue': 'Admin Hall', 'city': 'Toshkent',
            'starts_at': (timezone.now() + timedelta(days=7)).isoformat(), 'description': 'Admin test event',
            'artwork': 'music', 'published': 'on', 'rows': 2, 'seats_per_row': 3, 'price': 100000, 'vip_price': 200000,
            'seats-TOTAL_FORMS': 0, 'seats-INITIAL_FORMS': 0, 'seats-MIN_NUM_FORMS': 0, 'seats-MAX_NUM_FORMS': 0, **kwargs}

    def test_dashboard_and_model_pages_render(self):
        for path in ['/admin/', '/admin/booking/', '/admin/login/', '/admin/booking/event/add/',
                     f'/admin/booking/event/{self.event.pk}/change/'] + [f'/admin/booking/{name}/' for name in
                     ['event', 'booking', 'payment', 'ticket', 'paymentattempt', 'auditlog', 'newslettersubscription']]:
            with self.subTest(path=path):
                response = self.client.get(path, follow=True)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'admin/control.css')

    def test_admin_creation_builds_inventory_and_audit(self):
        response = self.client.post('/admin/booking/event/add/', self.data())
        self.assertEqual(response.status_code, 302, response.context['adminform'].form.errors if response.context else '')
        event = Event.objects.get(title='Created by admin')
        self.assertEqual(event.seats.count(), 12)
        self.assertEqual(set(event.seats.filter(sector='VIP').values_list('price', flat=True)), {200000})
        self.assertTrue(AuditLog.objects.filter(action='event.created', target=str(event.pk)).exists())

    def test_invalid_inventory_rejected_without_partial_event(self):
        response = self.client.post('/admin/booking/event/add/', self.data(rows=99))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Event.objects.filter(title='Created by admin').exists())

    def test_admin_edit_cannot_forge_seat_price_or_reservation(self):
        booking = reserve(self.customer, self.event.pk, [self.seat.pk])
        response = self.client.post(f'/admin/booking/event/{self.event.pk}/change/', self.data(
            title='Renamed', **{'seats-TOTAL_FORMS': 1, 'seats-INITIAL_FORMS': 1, 'seats-0-id': self.seat.pk,
                             'seats-0-event': self.event.pk, 'seats-0-price': 1, 'seats-0-reservation': ''}))
        self.assertEqual(response.status_code, 302, response.context['adminform'].form.errors if response.context else '')
        self.event.refresh_from_db(); self.seat.refresh_from_db()
        self.assertEqual(self.event.title, 'Renamed')
        self.assertEqual(self.seat.price, 120000)
        self.assertEqual(self.seat.reservation_id, booking.pk)

    @patch('booking.services.simulate_payment', return_value='admin-payment-reference')
    def test_financial_data_is_read_only_even_for_superuser(self, simulator):
        booking = reserve(self.customer, self.event.pk, [self.seat.pk])
        pay(self.customer, booking.pk)
        payment = Payment.objects.get(booking=booking)
        for model, pk in [('booking', booking.pk), ('payment', payment.pk)]:
            self.assertEqual(self.client.post(f'/admin/booking/{model}/{pk}/change/', {'total': 1, 'amount': 1}).status_code, 403)
        payment.refresh_from_db()
        self.assertEqual(payment.amount, 120000)

    def test_history_blocks_event_delete_and_bulk_action(self):
        reserve(self.customer, self.event.pk, [self.seat.pk])
        self.assertEqual(self.client.post(f'/admin/booking/event/{self.event.pk}/delete/', {'post': 'yes'}).status_code, 403)
        self.client.post('/admin/booking/event/', {'action': 'delete_selected', '_selected_action': self.event.pk, 'post': 'yes'})
        self.assertTrue(Event.objects.filter(pk=self.event.pk).exists())

    def test_event_manager_cannot_see_financial_dashboard_or_records(self):
        manager = User.objects.create_user('event-only', is_staff=True)
        manager.user_permissions.set(Permission.objects.filter(content_type__app_label='booking', codename__in=['view_event', 'add_event', 'change_event']))
        self.client.force_login(manager)
        response = self.client.get('/admin/')
        self.assertContains(response, 'Yaqin tadbirlar')
        self.assertNotContains(response, 'Demo tushum')
        self.assertEqual(self.client.get('/admin/booking/payment/').status_code, 403)
        self.assertEqual(self.client.get('/admin/booking/event/add/').status_code, 200)

    def test_customer_cannot_access_admin(self):
        self.client.force_login(self.customer)
        self.assertRedirects(self.client.get('/admin/'), '/admin/login/?next=/admin/')

    @override_settings(AUTH_RATE_LIMIT=1)
    def test_admin_login_is_rate_limited(self):
        self.client.logout()
        self.client.post('/admin/login/', {'username': 'invalid', 'password': 'invalid'})
        response = self.client.post('/admin/login/', {'username': 'invalid', 'password': 'invalid'})
        self.assertEqual(response.status_code, 429)
