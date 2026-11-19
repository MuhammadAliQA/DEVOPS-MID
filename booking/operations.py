import csv
import uuid
from datetime import timedelta
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from .forms import EventForm, NewEventForm
from .models import AuditLog, Booking, Event, Payment, PaymentAttempt, Seat, Ticket
from .services import BookingError, audit, cancel
from .permissions import operator_required




@operator_required('booking.view_payment')
def dashboard(request):
    today = timezone.localdate()
    start = today - timedelta(days=6)
    earned = Payment.objects.exclude(booking__status=Booking.Status.REFUNDED)
    daily = {entry['day']: entry['total'] for entry in earned.filter(created_at__date__gte=start)
             .annotate(day=TruncDate('created_at')).values('day').annotate(total=Sum('amount'))}
    peak = max(daily.values(), default=1) or 1
    chart = [{'day': start + timedelta(days=i), 'total': daily.get(start + timedelta(days=i), 0),
              'height': round(daily.get(start + timedelta(days=i), 0) / peak * 100)} for i in range(7)]
    valid_tickets = Ticket.objects.filter(item__booking__status=Booking.Status.PAID)
    tickets = valid_tickets.count()
    checked = valid_tickets.filter(checked_in_at__isnull=False).count()
    return render(request, 'operations/dashboard.html', {
        'section': 'dashboard', 'revenue': earned.aggregate(total=Sum('amount'))['total'] or 0,
        'sold': tickets, 'checked': checked, 'attendance': round(checked / tickets * 100) if tickets else 0,
        'active_holds': Booking.objects.filter(status='held', expires_at__gt=timezone.now()).count(),
        'event_count': Event.objects.filter(published=True, starts_at__gt=timezone.now()).count(),
        'chart': chart, 'recent': Booking.objects.select_related('user', 'event')[:6],
        'upcoming': Event.objects.filter(starts_at__gt=timezone.now())[:4], 'today': today,
    })


@operator_required('booking.view_event')
def events(request):
    queryset = Event.objects.all().annotate(seat_count=Count('seats', distinct=True)).order_by('starts_at', 'pk')
    query = request.GET.get('q', '')[:100]
    if query:
        queryset = queryset.filter(Q(title__icontains=query) | Q(venue__icontains=query))
    return render(request, 'operations/events.html', {'section': 'events', 'page': Paginator(queryset, 12).get_page(request.GET.get('page')), 'query': query})


@operator_required('booking.change_event')
def event_edit(request, pk=None):
    if pk is None and not request.user.has_perm('booking.add_event'):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
    event = get_object_or_404(Event, pk=pk) if pk else None
    form_class = EventForm if event else NewEventForm
    form = form_class(request.POST or None, request.FILES or None, instance=event)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            if event:
                Event.objects.select_for_update().get(pk=event.pk)
            saved = form.save()
            if not event:
                values = form.cleaned_data
                Seat.objects.bulk_create([
                    Seat(event=saved, sector=sector, row=chr(65 + row), number=number,
                         price=values['vip_price'] if sector == 'VIP' else values['price'])
                    for sector in ['A', 'VIP'] for row in range(values['rows'])
                    for number in range(1, values['seats_per_row'] + 1)])
            audit(request.user, 'event.updated' if event else 'event.created', saved.pk, title=saved.title)
        messages.success(request, 'Tadbir saqlandi.')
        return redirect('ops-events')
    return render(request, 'operations/event_form.html', {'section': 'events', 'form': form, 'event': event})


@operator_required('booking.delete_event')
@require_POST
def event_delete(request, pk):
    with transaction.atomic():
        event = get_object_or_404(Event.objects.select_for_update(), pk=pk)
        if Booking.objects.filter(event=event).exists():
            messages.error(request, 'Bron tarixi bor tadbirni o‘chirib bo‘lmaydi. Uni sotuvdan yashiring.')
            return redirect('ops-event-edit', pk=pk)
        audit(request.user, 'event.deleted', event.pk, title=event.title)
        event.delete()
    messages.success(request, 'Tadbir va uning bo‘sh inventari o‘chirildi.')
    return redirect('ops-events')


def _bookings(request):
    result = Booking.objects.select_related('user', 'event')
    state = request.GET.get('status', '')
    if state in Booking.Status.values:
        result = result.filter(status=state)
    query = request.GET.get('q', '')[:100]
    if query:
        result = result.filter(Q(user__username__icontains=query) | Q(event__title__icontains=query))
    return result


@operator_required('booking.view_booking')
def bookings(request):
    return render(request, 'operations/bookings.html', {'section': 'bookings',
        'page': Paginator(_bookings(request), 20).get_page(request.GET.get('page')),
        'statuses': Booking.Status.choices})


@operator_required('booking.change_booking')
def cancel_hold(request, pk):
    if request.method != 'POST':
        from django.http import HttpResponseNotAllowed
        return HttpResponseNotAllowed(['POST'])
    booking = get_object_or_404(Booking, pk=pk)
    try:
        cancel(booking.user, booking.pk, actor=request.user)
        messages.success(request, 'Bron bekor qilindi; joylar bo‘shatildi.')
    except BookingError as exc:
        messages.error(request, str(exc))
    return redirect('ops-bookings')


@operator_required('booking.view_payment')
def export(request):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="ticketflow-bookings.csv"'
    response.write('\ufeff')
    writer = csv.writer(response)
    writer.writerow(['Booking', 'Customer', 'Event', 'Status', 'Total UZS', 'Created'])
    def safe(value):
        value = str(value)
        return "'" + value if value.lstrip().startswith(('=', '+', '-', '@')) else value
    for booking in _bookings(request).iterator():
        writer.writerow([str(booking.pk), safe(booking.user.username), safe(booking.event.title),
                         booking.status, booking.total, booking.created_at.isoformat()])
    return response


@operator_required('booking.check_in_ticket')
def gate(request):
    if request.method == 'POST':
        raw = request.POST.get('ticket', '').strip().rstrip('/').split('/')[-1]
        try:
            ticket_id = uuid.UUID(raw)
        except (ValueError, AttributeError):
            messages.error(request, 'QR havola yoki chipta UUID kiriting.')
        else:
            if Ticket.objects.filter(pk=ticket_id).exists():
                return redirect('scan', pk=ticket_id)
            messages.error(request, 'Bunday chipta topilmadi.')
    valid = Ticket.objects.filter(item__booking__status=Booking.Status.PAID)
    return render(request, 'operations/gate.html', {'section': 'gate',
        'checked': valid.filter(checked_in_at__isnull=False).count(), 'total': valid.count(),
        'recent': valid.filter(checked_in_at__isnull=False).select_related('item__seat', 'item__booking__event').order_by('-checked_in_at')[:10]})


@operator_required('booking.view_auditlog')
def activity(request):
    rows = AuditLog.objects.select_related('actor').all()
    action = request.GET.get('action', '')[:50]
    if action:
        rows = rows.filter(action=action)
    return render(request, 'operations/activity.html', {'section': 'activity',
        'page': Paginator(rows, 30).get_page(request.GET.get('page')),
        'actions': AuditLog.objects.order_by('action').values_list('action', flat=True).distinct()})


@operator_required('booking.view_paymentattempt')
def payment_attempts(request):
    rows = PaymentAttempt.objects.select_related('booking__user', 'booking__event')
    state = request.GET.get('status', '')
    if state in PaymentAttempt.Status.values:
        rows = rows.filter(status=state)
    return render(request, 'operations/payments.html', {'section': 'payments',
        'page': Paginator(rows, 30).get_page(request.GET.get('page')), 'statuses': PaymentAttempt.Status.choices})
