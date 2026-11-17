from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .models import Booking, Event
from .services import BookingError, cancel, expire_event, pay, reserve, review_booking
from .forms import CheckoutForm


class ReservationInput(serializers.Serializer):
    event = serializers.IntegerField(min_value=1)
    seats = serializers.ListField(child=serializers.IntegerField(min_value=1), min_length=1, max_length=8)


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    form = UserCreationForm(request.data)
    if form.is_valid():
        user = form.save()
        return Response({'id': user.pk, 'username': user.username}, status=201)
    return Response(form.errors.get_json_data(), status=400)


@api_view(['GET'])
@permission_classes([AllowAny])
def events(request):
    return Response(list(Event.objects.filter(published=True, starts_at__gt=timezone.now()).values(
        'id', 'title', 'category', 'venue', 'starts_at', 'description', 'refundable')))


@api_view(['GET'])
@permission_classes([AllowAny])
def seats(request, pk):
    event = get_object_or_404(Event, pk=pk, published=True)
    expire_event(event.pk)
    return Response([{'id': seat.pk, 'sector': seat.sector, 'row': seat.row, 'number': seat.number,
                      'price': seat.price, 'available': seat.reservation_id is None and event.starts_at > timezone.now()}
                     for seat in event.seats.all()])


@api_view(['GET'])
def booking_detail(request, pk):
    booking = get_object_or_404(Booking, pk=pk, user=request.user)
    expire_event(booking.event_id)
    booking.refresh_from_db()
    return Response({'id': str(booking.pk), 'event': booking.event_id, 'total': booking.total,
                     'currency': 'UZS', 'status': booking.status, 'expires_at': booking.expires_at,
                     'tickets': [str(item.ticket.pk) for item in booking.items.select_related('ticket')
                                 if hasattr(item, 'ticket')]})


@api_view(['POST'])
def bookings(request):
    data = ReservationInput(data=request.data)
    data.is_valid(raise_exception=True)
    event_id = data.validated_data['event']
    get_object_or_404(Event, pk=event_id, published=True)
    try:
        booking = reserve(request.user, event_id, data.validated_data['seats'], request.headers.get('Idempotency-Key'))
    except BookingError as exc:
        return Response({'detail': str(exc), 'code': exc.code}, status=409)
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
        return Response({'detail': str(exc), 'code': exc.code}, status=status.HTTP_409_CONFLICT)
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
        return Response({'code': exc.code, 'detail': str(exc)}, status=409)
    return Response({'id': str(booking.pk), 'subtotal': booking.subtotal, 'discount': booking.discount,
                     'total': booking.total, 'currency': 'UZS', 'status': booking.status})


@api_view(['POST'])
def cancel_reservation(request, pk):
    get_object_or_404(Booking, pk=pk, user=request.user)
    try:
        cancel(request.user, pk)
    except BookingError as exc:
        return Response({'code': exc.code, 'detail': str(exc)}, status=409)
    return Response({'id': str(pk), 'status': 'cancelled'})
