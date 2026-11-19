from django.db.models import Count, Min, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .forms import CheckoutForm, RegisterForm
from .models import Booking, Event
from .services import BookingError, cancel, expire_event, expire_user_holds, pay, refund, reserve, review_booking

MAX_PAGE = 500


class ReservationInput(serializers.Serializer):
    event = serializers.IntegerField(min_value=1)
    seats = serializers.ListField(child=serializers.IntegerField(min_value=1), min_length=1, max_length=8)


def _error(exc, http_status=status.HTTP_409_CONFLICT):
    return Response({'detail': str(exc), 'code': exc.code}, status=http_status)


def _event_rows():
    """Published upcoming events with price and live availability in one query."""
    return (Event.objects.filter(published=True, starts_at__gt=timezone.now())
            .annotate(min_price=Min('seats__price'),
                      available_seats=Count('seats', filter=Q(seats__reservation__isnull=True)))
            .order_by('starts_at', 'pk'))


EVENT_FIELDS = ('id', 'title', 'category', 'venue', 'city', 'artist', 'starts_at', 'description', 'refundable',
                'min_price', 'available_seats')


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    form = RegisterForm(request.data)
    if form.is_valid():
        user = form.save()
        return Response({'id': user.pk, 'username': user.username}, status=201)
    return Response(form.errors.get_json_data(), status=400)


@api_view(['GET'])
@permission_classes([AllowAny])
def events(request):
    """Plain list (backwards compatible). Optional: q, category, venue, max_price,
    ordering=price, limit (<=500) and offset. The full match count is returned in
    the X-Total-Count header."""
    rows = _event_rows()
    params = request.query_params
    if params.get('q'):
        q = params['q'][:100]
        rows = rows.filter(Q(title__icontains=q) | Q(title_ru__icontains=q) | Q(title_en__icontains=q)
                           | Q(artist__icontains=q) | Q(venue__icontains=q))
    if params.get('category') in dict(Event._meta.get_field('category').choices):
        rows = rows.filter(category=params['category'])
    if params.get('venue'):
        rows = rows.filter(venue=params['venue'][:120])
    if params.get('max_price', '').isdigit():
        rows = rows.filter(min_price__lte=int(params['max_price']))
    if params.get('ordering') == 'price':
        rows = rows.order_by('min_price', 'starts_at', 'pk')
    total = rows.count()
    try:
        offset = max(0, int(params.get('offset', 0)))
        limit = min(max(1, int(params['limit'])), MAX_PAGE) if 'limit' in params else MAX_PAGE
    except ValueError:
        return Response({'detail': 'limit and offset must be integers.', 'code': 'invalid_pagination'}, status=400)
    response = Response(list(rows.values(*EVENT_FIELDS)[offset:offset + limit]))
    response['X-Total-Count'] = str(total)
    return response


@api_view(['GET'])
@permission_classes([AllowAny])
def event_detail(request, pk):
    event = get_object_or_404(_event_rows().filter(pk=pk).values(*EVENT_FIELDS, 'artist_photo', 'venue_photo', 'reference_image'))
    return Response(event)


@api_view(['GET'])
@permission_classes([AllowAny])
def seats(request, pk):
    event = get_object_or_404(Event, pk=pk, published=True)
    expire_event(event.pk)
    return Response([{'id': seat.pk, 'sector': seat.sector, 'row': seat.row, 'number': seat.number,
                      'price': seat.price, 'available': seat.reservation_id is None and event.starts_at > timezone.now()}
                     for seat in event.seats.all()])


def _booking_payload(booking):
    paid = booking.status == Booking.Status.PAID
    return {'id': str(booking.pk), 'event': booking.event_id, 'total': booking.total,
            'currency': 'UZS', 'status': booking.status, 'expires_at': booking.expires_at,
            'tickets': [str(item.ticket.pk) for item in booking.items.all() if paid and hasattr(item, 'ticket')]}


@api_view(['GET'])
def booking_detail(request, pk):
    booking = get_object_or_404(Booking, pk=pk, user=request.user)
    expire_event(booking.event_id)
    booking = Booking.objects.prefetch_related('items__ticket').get(pk=booking.pk)
    return Response(_booking_payload(booking))


@api_view(['GET', 'POST'])
def bookings(request):
    if request.method == 'GET':
        expire_user_holds(request.user)
        rows = Booking.objects.filter(user=request.user).prefetch_related('items__ticket')
        if request.query_params.get('status') in Booking.Status.values:
            rows = rows.filter(status=request.query_params['status'])
        return Response([_booking_payload(booking) for booking in rows[:100]])
    data = ReservationInput(data=request.data)
    data.is_valid(raise_exception=True)
    event_id = data.validated_data['event']
    get_object_or_404(Event, pk=event_id, published=True)
    try:
        booking = reserve(request.user, event_id, data.validated_data['seats'], request.headers.get('Idempotency-Key'))
    except BookingError as exc:
        return _error(exc)
    return Response({'id': str(booking.pk), 'total': booking.total, 'currency': 'UZS',
                     'expires_at': booking.expires_at, 'status': booking.status}, status=201)


@api_view(['POST'])
def payment(request, pk):
    get_object_or_404(Booking, pk=pk, user=request.user)
    outcome = request.data.get('outcome', 'approve')
    if outcome not in ('approve', 'decline'):
        return Response({'detail': 'Use approve or decline.'}, status=400)
    try:
        booking = pay(request.user, pk, outcome)
    except BookingError as exc:
        return _error(exc)
    return Response({'id': str(booking.pk), 'status': booking.status})


@api_view(['POST'])
def checkout(request, pk):
    get_object_or_404(Booking, pk=pk, user=request.user)
    form = CheckoutForm(request.data)
    if not form.is_valid():
        return Response(form.errors.get_json_data(), status=400)
    try:
        booking = review_booking(request.user, pk, form.cleaned_data)
    except BookingError as exc:
        return _error(exc)
    return Response({'id': str(booking.pk), 'subtotal': booking.subtotal, 'discount': booking.discount,
                     'total': booking.total, 'currency': 'UZS', 'status': booking.status})


@api_view(['POST'])
def cancel_reservation(request, pk):
    get_object_or_404(Booking, pk=pk, user=request.user)
    try:
        cancel(request.user, pk)
    except BookingError as exc:
        return _error(exc)
    return Response({'id': str(pk), 'status': 'cancelled'})


@api_view(['POST'])
def refund_booking(request, pk):
    get_object_or_404(Booking, pk=pk, user=request.user)
    try:
        booking = refund(request.user, pk)
    except BookingError as exc:
        return _error(exc)
    return Response({'id': str(booking.pk), 'status': booking.status, 'refunded_at': booking.refunded_at})
