import logging

from celery import shared_task
from django.db import close_old_connections

from booking.models import Booking
from booking.services import expire_event
from django.utils import timezone

logger = logging.getLogger("ticketly.worker")


@shared_task(
    bind=True,
    name="booking.expire_bookings",
    max_retries=3,
    default_retry_delay=10,
)
def expire_bookings_task(self):
    close_old_connections()

    try:
        event_ids = (
            Booking.objects
            .filter(
                status=Booking.Status.HELD,
                expires_at__lte=timezone.now(),
            )
            .order_by()
            .values_list("event_id", flat=True)
            .distinct()
        )

        expired_count = 0

        for event_id in event_ids.iterator():
            expired_count += expire_event(event_id)

        if expired_count:
            logger.info(
                "Celery expiry task completed: %s bookings expired",
                expired_count,
            )

        return {
            "expired_count": expired_count,
        }

    except Exception as exc:
        logger.exception("Celery booking expiry task failed")
        raise self.retry(exc=exc)
    finally:
        close_old_connections()
