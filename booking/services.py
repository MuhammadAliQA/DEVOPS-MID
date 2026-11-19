"""Reservations lock the customer first, then the event. Other inventory mutations
lock the event first, then the booking; none acquire a customer lock afterwards.

This intentionally serializes inventory changes per event. PostgreSQL is required
for concurrent use; SQLite is a single-user development convenience only.
"""
import hashlib
import hmac
import json
import uuid
from datetime import timedelta
from urllib.error import URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from .models import AuditLog, Booking, BookingSeat, Event, Payment, PaymentAttempt, Seat, Ticket


class BookingError(Exception):
    def __init__(self, message, code='booking_conflict'):
        super().__init__(message)
        self.code = code


def audit(actor, action, target, **details):
    return AuditLog.objects.create(actor=actor, action=action, target=str(target), details=details)


def _expire(event):
    """Release stale holds of an already locked event. Returns how many were expired."""
    stale_ids = list(Booking.objects.filter(event=event, status=Booking.Status.HELD,
                                            expires_at__lte=timezone.now()).values_list('pk', flat=True))
    if not stale_ids:
        return 0
    Seat.objects.filter(reservation_id__in=stale_ids).update(reservation=None)
    Booking.objects.filter(pk__in=stale_ids).update(status=Booking.Status.EXPIRED)
    AuditLog.objects.bulk_create([AuditLog(action='booking.expired', target=str(pk), details={'event': event.pk}) for pk in stale_ids])
    return len(stale_ids)


def expire_event(event_id):
    """Expire stale holds for one event.

    Page views and the 5-second seat-map poll call this constantly, so the common
    case (nothing stale) is a single indexed SELECT with no row lock and no writes.
    """
    if not Booking.objects.filter(event_id=event_id, status=Booking.Status.HELD,
                                  expires_at__lte=timezone.now()).exists():
        return 0
    with transaction.atomic():
        event = Event.objects.select_for_update().get(pk=event_id)
        return _expire(event)


def expire_user_holds(user):
    """Expire only this customer's overdue holds (used by the ticket wallet)."""
    event_ids = set(Booking.objects.filter(user=user, status=Booking.Status.HELD, expires_at__lte=timezone.now())
                    .order_by().values_list('event_id', flat=True))
    return sum(expire_event(event_id) for event_id in event_ids)


@transaction.atomic
def reserve(user, event_id, seat_ids, idempotency_key=None):
    if not seat_ids or len(seat_ids) > 8 or len(set(seat_ids)) != len(seat_ids):
        raise BookingError('1 dan 8 tagacha turli o‘rindiq tanlang.', 'invalid_selection')
    if idempotency_key:
        try:
            idempotency_key = uuid.UUID(str(idempotency_key))
        except (ValueError, AttributeError):
            raise BookingError('Bron identifikatori noto‘g‘ri.', 'invalid_idempotency_key')
    # Serialize one customer's reservations, including requests for different events.
    get_user_model().objects.select_for_update().get(pk=user.pk)
    if idempotency_key:
        existing = Booking.objects.filter(user=user, idempotency_key=idempotency_key).first()
        if existing:
            if existing.event_id != event_id or set(existing.items.values_list('seat_id', flat=True)) != set(seat_ids):
                raise BookingError('Bir identifikator bilan boshqa joylarni bron qilib bo‘lmaydi.', 'idempotency_conflict')
            expire_event(existing.event_id)
            existing.refresh_from_db()
            return existing
    active = Booking.objects.filter(user=user, status=Booking.Status.HELD, expires_at__gt=timezone.now()).count()
    if active >= getattr(settings, 'MAX_ACTIVE_HOLDS', 3):
        raise BookingError('Faol bronlar limitiga yetdingiz. Avval to‘lang yoki bronni bekor qiling.', 'hold_limit')
    event = Event.objects.select_for_update().get(pk=event_id)
    if not event.published or event.starts_at <= timezone.now():
        raise BookingError('Bu tadbir uchun bron yopilgan.', 'booking_closed')
    _expire(event)
    seats = list(Seat.objects.select_for_update().filter(event=event, pk__in=seat_ids))
    if len(seats) != len(seat_ids) or any(s.reservation_id for s in seats):
        raise BookingError('O‘rindiq band yoki noto‘g‘ri. Qayta tanlang.', 'seat_unavailable')
    booking = Booking.objects.create(user=user, event=event, total=sum(s.price for s in seats),
                                     expires_at=min(timezone.now() + timedelta(minutes=10), event.starts_at), idempotency_key=idempotency_key or None)
    BookingSeat.objects.bulk_create([BookingSeat(booking=booking, seat=s, price=s.price) for s in seats])
    Seat.objects.filter(pk__in=seat_ids).update(reservation=booking)
    audit(user, 'booking.reserved', booking.pk, event=event.pk, seats=seat_ids, amount=booking.total)
    return booking


def simulate_payment(booking, outcome):
    body = json.dumps({'booking': str(booking.pk), 'amount': booking.total,
                       'currency': 'UZS', 'outcome': outcome}, sort_keys=True).encode()
    signature = hmac.new(settings.PAYMENT_SECRET.encode(), body, hashlib.sha256).hexdigest()
    req = Request(settings.PAYMENT_URL + '/charge/', data=body,
                  headers={'Content-Type': 'application/json', 'X-Signature': signature})
    try:
        with urlopen(req, timeout=4) as response:
            data = json.load(response)
        if data.get('status') != 'approved':
            raise BookingError('Demo to‘lov rad etildi. Qayta urinishingiz mumkin.', 'payment_declined')
        expected = hashlib.sha256(f'demo:{booking.pk}:{booking.total}:UZS'.encode()).hexdigest()
        if data.get('reference') != expected:
            raise BookingError('Payment servis javobi noto‘g‘ri.', 'payment_unavailable')
        return expected
    except (URLError, TimeoutError, ValueError, OSError, TypeError, AttributeError) as exc:
        raise BookingError('Payment servisi hozir ishlamayapti. Bron tugashidan oldin qayta urining.', 'payment_unavailable') from exc


def pay(user, booking_id, outcome='approve'):
    if outcome not in ('approve', 'decline'):
        raise BookingError('To‘lov turi noto‘g‘ri.', 'invalid_outcome')
    # Remote I/O occurs outside the lock. Revalidate expiry and state afterwards.
    booking = Booking.objects.get(pk=booking_id, user=user)
    if booking.status == Booking.Status.PAID:
        return booking
    expire_event(booking.event_id)
    with transaction.atomic():
        event = Event.objects.select_for_update().get(pk=booking.event_id)
        booking = Booking.objects.select_for_update().get(pk=booking.pk)
        if booking.status == Booking.Status.PAID:
            return booking
        if booking.status != Booking.Status.HELD or booking.expires_at <= timezone.now() or event.starts_at <= timezone.now() or not event.published:
            raise BookingError('Bron faol emas.', 'inactive_booking')
        if PaymentAttempt.objects.filter(booking=booking, created_at__gte=timezone.now() - timedelta(minutes=1)).count() >= 10:
            raise BookingError('Juda ko‘p to‘lov urinishi. Bir daqiqadan so‘ng qayta urining.', 'payment_rate_limited')
        attempt = PaymentAttempt.objects.create(booking=booking)
    try:
        reference = simulate_payment(booking, outcome)
    except BookingError as exc:
        PaymentAttempt.objects.filter(pk=attempt.pk).update(status='failed', error_code=exc.code, finished_at=timezone.now())
        audit(user, 'payment.failed', booking.pk, attempt=str(attempt.pk), code=exc.code)
        raise
    rejected = False
    with transaction.atomic():
        event = Event.objects.select_for_update().get(pk=booking.event_id)
        booking = Booking.objects.select_for_update().get(pk=booking.pk)
        if booking.status == Booking.Status.PAID:
            PaymentAttempt.objects.filter(pk=attempt.pk).update(status='approved', finished_at=timezone.now())
            return booking
        if booking.status != Booking.Status.HELD or booking.expires_at <= timezone.now() or event.starts_at <= timezone.now() or not event.published:
            rejected = True
            PaymentAttempt.objects.filter(pk=attempt.pk).update(status='abandoned', error_code='inactive_booking', finished_at=timezone.now())
            audit(user, 'payment.abandoned', booking.pk, attempt=str(attempt.pk))
        else:
            Payment.objects.create(booking=booking, reference=reference, amount=booking.total)
            Ticket.objects.bulk_create([Ticket(item=item) for item in booking.items.all()])
            booking.status = Booking.Status.PAID
            booking.save(update_fields=['status'])
            PaymentAttempt.objects.filter(pk=attempt.pk).update(status='approved', finished_at=timezone.now())
            audit(user, 'payment.approved', booking.pk, amount=booking.total, attempt=str(attempt.pk))
    if rejected:
        raise BookingError('Bron muddati tugagan yoki bekor qilingan.', 'inactive_booking')
    return booking


@transaction.atomic
def cancel(user, booking_id, actor=None):
    booking = Booking.objects.get(pk=booking_id, user=user)
    Event.objects.select_for_update().get(pk=booking.event_id)
    booking = Booking.objects.select_for_update().get(pk=booking.pk)
    if booking.status != Booking.Status.HELD:
        raise BookingError('Faqat faol bronni bekor qilish mumkin.', 'inactive_booking')
    Seat.objects.filter(reservation=booking).update(reservation=None)
    booking.status = Booking.Status.CANCELLED
    booking.save(update_fields=['status'])
    audit(actor or user, 'booking.cancelled', booking.pk)


@transaction.atomic
def refund(user, booking_id, actor=None):
    """Refund a paid booking: release the seats and invalidate every ticket.

    Allowed only for refundable events, before the refund window closes and while
    no ticket has been scanned. No money moves: payments are simulated, so the
    Payment row stays as the historical record and revenue reports skip refunded
    bookings. Lock order matches the module docstring (event, then booking).
    """
    booking = Booking.objects.get(pk=booking_id, user=user)
    event = Event.objects.select_for_update().get(pk=booking.event_id)
    booking = Booking.objects.select_for_update().get(pk=booking.pk)
    if booking.status != Booking.Status.PAID:
        raise BookingError('Faqat to‘langan bronni qaytarish mumkin.', 'refund_not_allowed')
    if not event.refundable:
        raise BookingError('Bu tadbir uchun to‘lov qaytarilmaydi.', 'refund_not_allowed')
    window = timedelta(hours=getattr(settings, 'REFUND_WINDOW_HOURS', 24))
    if event.starts_at - timezone.now() < window:
        raise BookingError('Qaytarish muddati o‘tgan.', 'refund_window_closed')
    if Ticket.objects.filter(item__booking=booking, checked_in_at__isnull=False).exists():
        raise BookingError('Ishlatilgan chipta uchun to‘lov qaytarilmaydi.', 'refund_not_allowed')
    Seat.objects.filter(reservation=booking).update(reservation=None)
    booking.status = Booking.Status.REFUNDED
    booking.refunded_at = timezone.now()
    booking.save(update_fields=['status', 'refunded_at'])
    audit(actor or user, 'booking.refunded', booking.pk, amount=booking.total, event=event.pk)
    return booking


def can_refund(booking):
    """Cheap UI hint; refund() stays the authority and re-checks under locks."""
    event = booking.event
    window = timedelta(hours=getattr(settings, 'REFUND_WINDOW_HOURS', 24))
    return (booking.status == Booking.Status.PAID and event.refundable
            and event.starts_at - timezone.now() >= window)


@transaction.atomic
def check_in(ticket_id, actor=None):
    ticket = Ticket.objects.select_for_update().get(pk=ticket_id)
    if ticket.item.booking.status != Booking.Status.PAID:
        raise BookingError('Chipta haqiqiy emas.', 'ticket_invalid')
    if ticket.checked_in_at:
        raise BookingError('Bu chipta avval ishlatilgan.', 'ticket_used')
    ticket.checked_in_at = timezone.now()
    ticket.save(update_fields=['checked_in_at'])
    audit(actor, 'ticket.checked_in', ticket.pk, event=ticket.item.booking.event_id)
    return ticket


@transaction.atomic
def review_booking(user, booking_id, contact):
    booking = Booking.objects.get(pk=booking_id, user=user)
    Event.objects.select_for_update().get(pk=booking.event_id)
    booking = Booking.objects.select_for_update().get(pk=booking_id)
    if booking.status != Booking.Status.HELD or booking.expires_at <= timezone.now():
        raise BookingError('Bron faol emas.', 'inactive_booking')
    code = contact.get('promo_code', '').strip().upper()
    if code not in ('', 'TICKETLY10'):
        raise BookingError('Promokod noto‘g‘ri.', 'promo_invalid')
    if booking.payment_attempts.exists() and code != booking.promo_code:
        raise BookingError('Narx o‘zgarmaydi.', 'pricing_locked')
    subtotal = sum(booking.items.values_list('price', flat=True))
    booking.discount = subtotal // 10 if code else 0
    booking.total = subtotal - booking.discount
    booking.promo_code = code
    for field in ('contact_name', 'contact_email', 'contact_phone'):
        setattr(booking, field, contact.get(field, ''))
    booking.save(update_fields=['discount', 'total', 'promo_code', 'contact_name', 'contact_email', 'contact_phone'])
    audit(user, 'booking.reviewed', booking.pk, discount=booking.discount)
    return booking
