from datetime import timedelta
from unittest.mock import patch
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone, translation
from .models import Booking, Event, NewsletterSubscription, Payment, PaymentAttempt, Seat, Ticket
from .services import BookingError, reserve, review_booking, pay
from .translations import COPY


class FigmaJourneyTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('figma', password='test-strong-2299')
        self.other = User.objects.create_user('other')
        self.event = Event.objects.create(title='Toshkent kechasi', title_ru='Ташкентский вечер', title_en='Tashkent night',
            artist='Demo artist', category='festival', venue='Demo venue', published=True,
            starts_at=timezone.now() + timedelta(days=3))
        self.seat = Seat.objects.create(event=self.event, sector='VIP', row='A', number=1, price=100005)
        self.client.force_login(self.user)
        self.contact = dict(contact_name='Test Person', contact_email='test@example.com', contact_phone='+998901234567', promo_code='TICKETLY10')

    def hold(self):
        return reserve(self.user, self.event.pk, [self.seat.pk])

    def test_public_routes_render_in_all_three_languages(self):
        for lang in ('uz', 'ru', 'en'):
            self.client.post('/i18n/setlang/', {'language': lang, 'next': '/'})
            for route in ('/', '/events/', '/artists/', '/venues/', '/profile/', '/help/', '/terms/', '/privacy/',
                          '/tickets/', '/accounts/login/', '/accounts/register/', f'/events/{self.event.pk}/', f'/events/{self.event.pk}/seats/'):
                with self.subTest(lang=lang, route=route):
                    response = self.client.get(route)
                    self.assertEqual(response.status_code, 200)
                    self.assertContains(response, 'figma.css')
                    self.assertContains(response, f'<html lang="{lang}">')
        self.assertContains(self.client.get('/events/?category=festival'), 'Tashkent night')

    def test_language_cookie_and_localized_event(self):
        response = self.client.post('/i18n/setlang/', {'language': 'ru', 'next': '/events/'})
        self.assertEqual(response.cookies['ticketflow_language'].value, 'ru')
        self.assertContains(self.client.get('/events/'), 'Ташкентский вечер')
        self.assertContains(self.client.get('/events/'), 'События')
        for values in COPY.values():
            self.assertEqual(len(values), 3)
            self.assertNotIn('??', values[1])
            self.assertTrue(all(values))

    @patch('booking.services.simulate_payment', return_value='figma-paid')
    def test_contact_discount_payment_success_and_private_ticket(self, simulator):
        booking = self.hold()
        response = self.client.post(reverse('checkout', args=[booking.pk]), self.contact)
        self.assertRedirects(response, reverse('payment-page', args=[booking.pk]))
        booking.refresh_from_db()
        self.assertEqual((booking.total, booking.discount, booking.contact_email), (90005, 10000, 'test@example.com'))
        self.assertEqual(self.client.post(reverse('payment', args=[booking.pk]), {'outcome': 'approve'}).url, reverse('success', args=[booking.pk]))
        self.assertEqual(Payment.objects.get(booking=booking).amount, 90005)
        self.assertEqual(self.client.get(reverse('success', args=[booking.pk])).status_code, 200)
        self.assertContains(self.client.get('/tickets/'), str(Ticket.objects.get(item__booking=booking).pk))
        self.client.force_login(self.other)
        for name in ('checkout', 'payment-page', 'success'):
            self.assertEqual(self.client.get(reverse(name, args=[booking.pk])).status_code, 404)

    def test_invalid_contact_and_promo_do_not_modify_booking(self):
        booking = self.hold()
        response = self.client.post(reverse('checkout', args=[booking.pk]), {**self.contact, 'contact_email': 'invalid'})
        self.assertEqual(response.status_code, 200)
        with self.assertRaises(BookingError):
            review_booking(self.user, booking.pk, {**self.contact, 'promo_code': 'FREE'})
        booking.refresh_from_db()
        self.assertEqual(booking.discount, 0)

    def test_discount_is_idempotent_and_frozen_after_payment_attempt(self):
        booking = self.hold()
        for _ in range(2):
            review_booking(self.user, booking.pk, self.contact)
        booking.refresh_from_db()
        self.assertEqual(booking.total, 90005)
        PaymentAttempt.objects.create(booking=booking, status='failed')
        with self.assertRaises(BookingError) as exc:
            review_booking(self.user, booking.pk, {**self.contact, 'promo_code': ''})
        self.assertEqual(exc.exception.code, 'pricing_locked')
        review_booking(self.user, booking.pk, {**self.contact, 'contact_name': 'Updated Name'})
        booking.refresh_from_db()
        self.assertEqual(booking.total, 90005)

    def test_expired_booking_cannot_be_reviewed_or_show_payment_controls(self):
        booking = self.hold()
        Booking.objects.filter(pk=booking.pk).update(expires_at=timezone.now() - timedelta(seconds=1))
        with self.assertRaises(BookingError): review_booking(self.user, booking.pk, self.contact)
        response = self.client.get(reverse('payment-page', args=[booking.pk]))
        self.assertNotContains(response, 'value="approve"')
        self.assertEqual(self.client.get(reverse('success', args=[booking.pk])).status_code, 404)

    def test_profile_can_only_modify_current_user(self):
        self.client.post('/profile/', {'first_name': 'New', 'last_name': 'Name', 'email': 'new@example.com', 'is_staff': 'true', 'id': self.other.pk})
        self.user.refresh_from_db(); self.other.refresh_from_db()
        self.assertEqual(self.user.first_name, 'New')
        self.assertFalse(self.user.is_staff)
        self.assertEqual(self.other.first_name, '')

    def test_subscription_validated_and_case_deduplicated(self):
        for email in ('not-an-email', 'Test@example.com', 'test@example.com'):
            self.client.post('/subscribe/', {'email': email})
        self.assertEqual(NewsletterSubscription.objects.count(), 1)

    def test_directories_never_use_concert_posters_for_people_or_venues(self):
        self.event.reference_image = 'https://example.com/concert.jpg'
        self.event.save()
        for route in ('/artists/', '/venues/'):
            response = self.client.get(route)
            self.assertNotContains(response, 'https://example.com/concert.jpg')
            self.assertContains(response, 'portrait-placeholder')
        self.event.artist_photo = 'https://example.com/artist-portrait.jpg'
        self.event.venue_photo = 'https://example.com/venue-building.jpg'
        self.event.save()
        self.assertContains(self.client.get('/artists/'), self.event.artist_photo)
        self.assertNotContains(self.client.get('/artists/'), self.event.venue_photo)
        self.assertContains(self.client.get('/venues/'), self.event.venue_photo)
        self.assertNotContains(self.client.get('/venues/'), self.event.artist_photo)
