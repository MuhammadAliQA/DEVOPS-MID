"""Regression tests for the audit fixes and the refund / API / cheap-expiry work."""
import uuid
from datetime import timedelta
from unittest.mock import patch
from .models import AuditLog, Booking, Event, Seat, Ticket
from .tasks import expire_bookings_task
from django.contrib.auth.models import Permission, User
from django.db import connection
from django.test import Client, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from .models import Booking, Event, Seat, Ticket
from .services import BookingError, can_refund, check_in, expire_event, pay, refund, reserve

PASSWORD = 'Example-strong-2048'


def make_event(days=5, title='Test concert', venue='Tashkent', refundable=True, seats=3, **extra):
    event = Event.objects.create(title=title, category='music', venue=venue, refundable=refundable,
                                 starts_at=timezone.now() + timedelta(days=days), published=True, **extra)
    return event, [Seat.objects.create(event=event, row='A', number=i, price=100000) for i in range(1, seats + 1)]


def paid_booking(user, event, seat):
    booking = reserve(user, event.pk, [seat.pk])
    with patch('booking.services.simulate_payment', return_value=f'ref-{uuid.uuid4().hex}'):
        return pay(user, booking.pk)


def gate_staff(name='gate'):
    staff = User.objects.create_user(name, password=PASSWORD, is_staff=True)
    staff.user_permissions.add(Permission.objects.get(codename='check_in_ticket'))
    return staff


class CheapExpiryTests(TestCase):
    def test_nothing_stale_is_one_read_without_writes(self):
        event, _ = make_event()
        with CaptureQueriesContext(connection) as queries:
            self.assertEqual(expire_event(event.pk), 0)
        self.assertEqual(len(queries), 1)
        self.assertTrue(queries[0]['sql'].lstrip().upper().startswith('SELECT'))

    def test_celery_task_expires_booking_and_is_idempotent(self):
        user = User.objects.create_user('celery-expiry-user')
        event, seats = make_event()

        booking = reserve(user, event.pk, [seats[0].pk])

        Booking.objects.filter(pk=booking.pk).update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )

        with patch("booking.tasks.close_old_connections"):
            result = expire_bookings_task.apply(throw=True).get()

        self.assertEqual(result['expired_count'], 1)

        booking.refresh_from_db()
        seats[0].refresh_from_db()

        self.assertEqual(booking.status, Booking.Status.EXPIRED)
        self.assertIsNone(seats[0].reservation_id)

        self.assertTrue(
            AuditLog.objects.filter(
                action='booking.expired',
                target=str(booking.pk),
            ).exists()
        )

        with patch("booking.tasks.close_old_connections"):
            second_result = expire_bookings_task.apply(throw=True).get()
        self.assertEqual(second_result['expired_count'], 0)

        self.assertEqual(
            AuditLog.objects.filter(
                action='booking.expired',
                target=str(booking.pk),
            ).count(),
            1,
        )

    def test_stale_hold_is_released(self):
        user = User.objects.create_user('u', password=PASSWORD)
        event, seats = make_event()
        booking = reserve(user, event.pk, [seats[0].pk])
        Booking.objects.filter(pk=booking.pk).update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertEqual(expire_event(event.pk), 1)
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.EXPIRED)
        self.assertFalse(Seat.objects.filter(reservation=booking).exists())


class RefundTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('buyer', password=PASSWORD)
        self.other = User.objects.create_user('stranger', password=PASSWORD)
        self.event, self.seats = make_event(days=5)

    def test_refund_releases_seats_and_invalidates_tickets(self):
        booking = paid_booking(self.user, self.event, self.seats[0])
        ticket = Ticket.objects.get(item__booking=booking)
        refunded = refund(self.user, booking.pk)
        self.assertEqual(refunded.status, Booking.Status.REFUNDED)
        self.assertIsNotNone(refunded.refunded_at)
        self.assertFalse(Seat.objects.filter(reservation=booking).exists())
        with self.assertRaises(BookingError) as caught:
            check_in(ticket.pk, self.user)
        self.assertEqual(caught.exception.code, 'ticket_invalid')
        # the seat can be sold again
        self.assertEqual(reserve(self.other, self.event.pk, [self.seats[0].pk]).status, Booking.Status.HELD)

    def test_refund_rules(self):
        near, near_seats = make_event(days=0, title='Tonight')
        Event.objects.filter(pk=near.pk).update(starts_at=timezone.now() + timedelta(hours=3))
        locked, locked_seats = make_event(refundable=False, title='No refunds')
        cases = {'window_closed': (near, near_seats[0], 'refund_window_closed'),
                 'not_refundable': (locked, locked_seats[0], 'refund_not_allowed')}
        for name, (event, seat, code) in cases.items():
            with self.subTest(name):
                booking = paid_booking(self.user, event, seat)
                self.assertFalse(can_refund(Booking.objects.get(pk=booking.pk)))
                with self.assertRaises(BookingError) as caught:
                    refund(self.user, booking.pk)
                self.assertEqual(caught.exception.code, code)

    def test_held_or_used_or_foreign_bookings_cannot_be_refunded(self):
        held = reserve(self.user, self.event.pk, [self.seats[0].pk])
        with self.assertRaises(BookingError):
            refund(self.user, held.pk)
        paid = paid_booking(self.user, self.event, self.seats[1])
        check_in(Ticket.objects.get(item__booking=paid).pk, gate_staff())
        with self.assertRaises(BookingError) as caught:
            refund(self.user, paid.pk)
        self.assertEqual(caught.exception.code, 'refund_not_allowed')
        with self.assertRaises(Booking.DoesNotExist):
            refund(self.other, paid.pk)

    def test_refund_view_and_wallet_button(self):
        booking = paid_booking(self.user, self.event, self.seats[0])
        client = Client(); client.force_login(self.user)
        self.assertContains(client.get(reverse('wallet')), reverse('refund', args=[booking.pk]))
        stranger = Client(); stranger.force_login(self.other)
        self.assertEqual(stranger.post(reverse('refund', args=[booking.pk])).status_code, 404)
        self.assertEqual(client.get(reverse('refund', args=[booking.pk])).status_code, 405)
        response = client.post(reverse('refund', args=[booking.pk]), follow=True)
        self.assertEqual(response.status_code, 200)
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.REFUNDED)
        self.assertNotContains(client.get(reverse('wallet')), reverse('refund', args=[booking.pk]))

    def test_refund_api(self):
        booking = paid_booking(self.user, self.event, self.seats[0])
        client = Client(); client.force_login(self.user)
        self.assertEqual(client.get(f'/api/bookings/{booking.pk}/').json()['tickets'].__len__(), 1)
        response = client.post(f'/api/bookings/{booking.pk}/refund/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'refunded')
        self.assertEqual(client.get(f'/api/bookings/{booking.pk}/').json()['tickets'], [])
        again = client.post(f'/api/bookings/{booking.pk}/refund/')
        self.assertEqual((again.status_code, again.json()['code']), (409, 'refund_not_allowed'))

    def test_refunded_money_leaves_revenue_and_ticket_counts(self):
        booking = paid_booking(self.user, self.event, self.seats[0])
        boss = User.objects.create_superuser('boss', password=PASSWORD)
        client = Client(); client.force_login(boss)
        self.assertEqual(client.get(reverse('ops-dashboard')).context['sold'], 1)
        refund(self.user, booking.pk)
        context = client.get(reverse('ops-dashboard')).context
        self.assertEqual((context['sold'], context['revenue']), (0, 0))


class FixedBugTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('fan', password=PASSWORD)
        self.client = Client(); self.client.force_login(self.user)

    def test_venue_filter_has_no_duplicates(self):
        make_event(days=3, title='One', venue='Humo Arena')
        make_event(days=9, title='Two', venue='Humo Arena')
        make_event(days=12, title='Three', venue='Navoiy')
        self.assertEqual(list(self.client.get('/events/').context['venues']), ['Humo Arena', 'Navoiy'])

    def test_home_without_events_has_no_stray_dash(self):
        html = self.client.get('/').content.decode()
        self.assertNotIn('<p> — </p>', html)
        self.assertNotIn('<p>—', html.replace(' ', ''))

    def test_events_without_seats_show_dash_instead_of_zero(self):
        Event.objects.create(title='Empty hall', category='music', venue='V', description='d', published=True,
                             starts_at=timezone.now() + timedelta(days=4))
        html = self.client.get('/events/').content.decode()
        self.assertNotIn('0 <small>UZS</small>', html)

    def test_gate_unknown_ticket_is_a_message_not_a_404(self):
        gate = Client(); gate.force_login(gate_staff())
        for value in (str(uuid.uuid4()), 'not-a-uuid'):
            response = gate.post(reverse('ops-gate'), {'ticket': value})
            self.assertEqual(response.status_code, 200, value)
        self.assertContains(gate.post(reverse('ops-gate'), {'ticket': str(uuid.uuid4())}), 'topilmadi')

    def test_scan_reports_the_real_reason(self):
        event, seats = make_event()
        booking = paid_booking(self.user, event, seats[0])
        ticket = Ticket.objects.get(item__booking=booking)
        gate = Client(); gate.force_login(gate_staff())
        gate.post(reverse('scan', args=[ticket.pk]))
        second = gate.post(reverse('scan', args=[ticket.pk]), follow=True)
        text = second.content.decode()
        self.assertIn('avval ishlatilgan', text)
        self.assertNotIn('Joy band', text)

    def test_register_honours_next_and_blocks_duplicate_emails(self):
        guest = Client()
        form = {'username': 'newbie', 'email': 'Same@Example.com', 'password1': 'Zx-9-long-pass-77', 'password2': 'Zx-9-long-pass-77'}
        response = guest.post('/accounts/register/?next=/tickets/', {**form, 'next': '/tickets/'})
        self.assertEqual((response.status_code, response['Location']), (302, '/tickets/'))
        self.assertEqual(User.objects.get(username='newbie').email, 'same@example.com')
        evil = Client().post('/accounts/register/', {**form, 'username': 'x2', 'email': '', 'next': 'https://evil.example/'})
        self.assertEqual(evil['Location'], reverse('home'))
        clash = Client().post('/accounts/register/', {**form, 'username': 'newbie2'})
        self.assertEqual(clash.status_code, 200)
        self.assertFalse(User.objects.filter(username='newbie2').exists())
        api = Client().post('/api/register/', {**form, 'username': 'newbie3'}, content_type='application/json')
        self.assertEqual(api.status_code, 400)

    def test_profile_rejects_email_used_by_someone_else(self):
        User.objects.create_user('owner', email='taken@example.com', password=PASSWORD)
        response = self.client.post('/profile/', {'first_name': 'A', 'last_name': 'B', 'email': 'TAKEN@example.com'})
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertNotEqual(self.user.email, 'taken@example.com')

    def test_favorite_returns_json_for_fetch(self):
        event, _ = make_event()
        url = reverse('favorite', args=[event.pk])
        on = self.client.post(url, headers={'X-Requested-With': 'fetch'})
        self.assertEqual(on.json(), {'favorite': True, 'event': event.pk})
        off = self.client.post(url, headers={'X-Requested-With': 'fetch'})
        self.assertFalse(off.json()['favorite'])
        self.assertEqual(self.client.post(url).status_code, 302)  # classic form flow still redirects

    def test_error_pages_are_branded_and_localized(self):
        response = Client().get('/definitely-missing/')
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, 'Sahifa topilmadi', status_code=404)

    def test_typographic_typo_in_search_placeholder_is_gone(self):
        self.assertNotIn('izlang’', self.client.get('/').content.decode())

    def test_directory_cards_carry_counts_and_photos(self):
        make_event(days=3, venue='Humo Arena', venue_photo='https://example.com/a.jpg')
        make_event(days=6, title='B', venue='Humo Arena')
        cards = self.client.get('/venues/').context['cards']
        self.assertEqual([(c['name'], c['count']) for c in cards], [('Humo Arena', 2)])
        self.assertEqual(cards[0]['image'], 'https://example.com/a.jpg')


class ApiImprovementTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('apiuser', password=PASSWORD)
        self.a, self.a_seats = make_event(days=3, title='Jazz night', venue='Humo Arena')
        self.b, _ = make_event(days=6, title='Rock fest', venue='Navoiy')
        Seat.objects.filter(event=self.b).update(price=500000)
        self.client = Client(); self.client.force_login(self.user)

    def test_list_is_backwards_compatible_and_carries_availability(self):
        response = self.client.get('/api/events/')
        data = response.json()
        self.assertEqual([row['title'] for row in data], ['Jazz night', 'Rock fest'])
        self.assertEqual((data[0]['min_price'], data[0]['available_seats']), (100000, 3))
        self.assertEqual(response['X-Total-Count'], '2')

    def test_filters_ordering_and_pagination(self):
        get = lambda query: self.client.get('/api/events/' + query)
        self.assertEqual([r['title'] for r in get('?q=rock').json()], ['Rock fest'])
        self.assertEqual([r['title'] for r in get('?venue=Navoiy').json()], ['Rock fest'])
        self.assertEqual([r['title'] for r in get('?max_price=200000').json()], ['Jazz night'])
        self.assertEqual([r['title'] for r in get('?ordering=price').json()], ['Jazz night', 'Rock fest'])
        page = get('?limit=1&offset=1')
        self.assertEqual(([r['title'] for r in page.json()], page['X-Total-Count']), (['Rock fest'], '2'))
        self.assertEqual(get('?limit=abc').status_code, 400)
        self.assertEqual(get('?category=nonsense').json().__len__(), 2)  # unknown category is ignored

    def test_availability_drops_after_reserving(self):
        reserve(self.user, self.a.pk, [self.a_seats[0].pk])
        self.assertEqual(self.client.get('/api/events/').json()[0]['available_seats'], 2)

    def test_event_detail(self):
        data = self.client.get(f'/api/events/{self.a.pk}/').json()
        self.assertEqual((data['title'], data['venue']), ('Jazz night', 'Humo Arena'))
        self.assertEqual(self.client.get('/api/events/999999/').status_code, 404)
        Event.objects.filter(pk=self.a.pk).update(published=False)
        self.assertEqual(self.client.get(f'/api/events/{self.a.pk}/').status_code, 404)

    def test_my_bookings_listing_is_private_and_filterable(self):
        mine = reserve(self.user, self.a.pk, [self.a_seats[0].pk])
        other = User.objects.create_user('someone', password=PASSWORD)
        reserve(other, self.a.pk, [self.a_seats[1].pk])
        rows = self.client.get('/api/bookings/').json()
        self.assertEqual([row['id'] for row in rows], [str(mine.pk)])
        self.assertEqual(self.client.get('/api/bookings/?status=paid').json(), [])
        self.assertIn(Client().get('/api/bookings/').status_code, (401, 403))

    def test_specific_error_codes_reach_api_clients(self):
        reserve(self.user, self.a.pk, [self.a_seats[0].pk])
        rival = User.objects.create_user('rival', password=PASSWORD)
        rival_client = Client(); rival_client.force_login(rival)
        response = rival_client.post('/api/bookings/', {'event': self.a.pk, 'seats': [self.a_seats[0].pk]}, content_type='application/json')
        self.assertEqual((response.status_code, response.json()['code']), (409, 'seat_unavailable'))

    def test_user_throttle_is_configured(self):
        from django.conf import settings
        classes = settings.REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES']
        self.assertIn('rest_framework.throttling.UserRateThrottle', classes)
        self.assertIn('user', settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'])
