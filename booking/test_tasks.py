from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TransactionTestCase
from django.utils import timezone

from booking.models import AuditLog, Booking, Event, Seat
from booking.services import reserve
from booking.tasks import expire_bookings_task


class BookingExpiryTaskTests(TransactionTestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="celery_test_user",
            password="Test-password-123",
        )

        self.event = Event.objects.create(
            title="Celery expiry test",
            category="music",
            venue="Test venue",
            starts_at=timezone.now() + timedelta(days=5),
            published=True,
        )

        self.seat = Seat.objects.create(
            event=self.event,
            row="A",
            number=1,
            price=100000,
        )

    def test_task_expires_stale_booking_and_releases_seat(self):
        booking = reserve(
            self.user,
            self.event.pk,
            [self.seat.pk],
        )

        Booking.objects.filter(pk=booking.pk).update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )

        with patch("booking.tasks.close_old_connections"):
            result = expire_bookings_task.apply(throw=True).get()

        booking.refresh_from_db()
        self.seat.refresh_from_db()

        self.assertEqual(result, {"expired_count": 1})
        self.assertEqual(booking.status, Booking.Status.EXPIRED)
        self.assertIsNone(self.seat.reservation_id)

        self.assertTrue(
            AuditLog.objects.filter(
                action="booking.expired",
                target=str(booking.pk),
            ).exists()
        )

    def test_task_returns_zero_when_no_booking_is_expired(self):
        with patch("booking.tasks.close_old_connections"):
            result = expire_bookings_task.apply(throw=True).get()

        self.assertEqual(result, {"expired_count": 0})
