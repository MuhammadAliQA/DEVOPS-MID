from datetime import timedelta
import uuid
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.db import connection
from django.db.models import Min, Max, Count, Q
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from .forms import CheckoutForm, DiscoveryForm, ProfileForm, SubscriptionForm
from .models import Booking, Event, Favorite, NewsletterSubscription, Ticket
from .services import BookingError, cancel, check_in, expire_event, pay, reserve, review_booking
from .qr import render_svg
from .permissions import operator_required
from .translations import tr, language


def home(request, listing=False):
    if request.GET.get('favorites') == '1' and not request.user.is_authenticated:
        return redirect('/accounts/login/?next=/%3Ffavorites%3D1')
    events = Event.objects.filter(published=True, starts_at__gt=timezone.now()).annotate(min_price=Min('seats__price'))
    form = DiscoveryForm(request.GET)
    if form.is_valid():
        f = form.cleaned_data
        if f['q']:
            events = events.filter(Q(title__icontains=f['q']) | Q(title_ru__icontains=f['q']) | Q(title_en__icontains=f['q']) | Q(artist__icontains=f['q']) | Q(venue__icontains=f['q']))
        for field in ['category', 'venue']:
            if f[field]:
                events = events.filter(**{field: f[field]})
        if f['date']:
            events = events.filter(starts_at__date=f['date'])
        if f['max_price'] is not None:
            events = events.filter(min_price__lte=f['max_price'])
        if f['sort'] == 'price':
            events = events.order_by('min_price', 'starts_at')
    favorites = []
    if request.user.is_authenticated:
        favorites = list(Favorite.objects.filter(user=request.user).values_list('event_id', flat=True))
        if request.GET.get('favorites') == '1':
            events = events.filter(pk__in=favorites)
    venue_cards = []
    for venue in Event.objects.filter(published=True, starts_at__gt=timezone.now()).values('venue', 'city').annotate(count=Count('pk'))[:3]:
        sample = Event.objects.filter(published=True, venue=venue['venue']).first()
        venue_cards.append({**venue, 'image': sample.venue_photo})
    return render(request, 'events.html' if listing or request.GET else 'home.html', {'events': events, 'form': form, 'favorites': favorites, 'venue_cards': venue_cards,
                                       'categories': [('all', 'zap'), ('music', 'music'), ('sport', 'users'), ('theatre', 'sparkles'), ('festival', 'calendar'), ('cinema', 'ticket'), ('tech', 'zap')],
                                       'featured': events.first(),
                                       'venues': Event.objects.filter(published=True).values_list('venue', flat=True).distinct()})


def detail(request, pk):
    event = get_object_or_404(Event, pk=pk, published=True)
    expire_event(event.pk)
    total = event.seats.count()
    sold = event.seats.filter(reservation__status='paid').count()
    return render(request, 'detail.html', {'event': event,
        'tiers': event.seats.values('sector').annotate(price=Min('price')).order_by('sector'),
        'min_price': event.seats.aggregate(price=Min('price'))['price'],
        'available': event.seats.filter(reservation=None).count(),
        'sold_percent': round(sold / total * 100) if total else 0,
        'favorite': request.user.is_authenticated and Favorite.objects.filter(user=request.user, event=event).exists(),
        'closed': event.starts_at <= timezone.now()})


@login_required
def seat_selection(request, pk):
    event = get_object_or_404(Event, pk=pk, published=True)
    expire_event(event.pk)
    return render(request, 'seats.html', {'event': event, 'seats': event.seats.select_related('reservation'),
        'sectors': event.seats.values_list('sector', flat=True).distinct(),
        'reservation_key': str(uuid.uuid4()), 'closed': event.starts_at <= timezone.now(), 'no_footer': True})


def poster(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if not event.published and not (request.user.is_staff and request.user.has_perm('booking.view_event')):
        raise Http404
    if not event.poster:
        raise Http404
    try:
        response = FileResponse(event.poster.open('rb'))
    except FileNotFoundError:
        raise Http404
    response['Cache-Control'] = 'public, max-age=60' if event.published else 'private, no-store'
    return response


def register(request):
    form = UserCreationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        login(request, form.save())
        return redirect('home')
    return render(request, 'registration/register.html', {'form': form})


@login_required
@require_POST
def book(request, pk):
    get_object_or_404(Event, pk=pk, published=True)
    try:
        seat_ids = [int(s) for s in request.POST.getlist('seats')]
        booking = reserve(request.user, pk, seat_ids, request.POST.get('idempotency_key'))
        return redirect('checkout', pk=booking.pk)
    except (BookingError, ValueError) as exc:
        messages.error(request, tr(exc.code) if isinstance(exc, BookingError) else tr('booking_conflict'))
        return redirect('seats', pk=pk)


@login_required
def checkout(request, pk):
    booking = get_object_or_404(Booking, pk=pk, user=request.user)
    expire_event(booking.event_id)
    booking.refresh_from_db()
    form = CheckoutForm(request.POST or None, initial={
        'contact_name': booking.contact_name or request.user.get_full_name() or request.user.username,
        'contact_email': booking.contact_email or request.user.email,
        'contact_phone': booking.contact_phone, 'promo_code': booking.promo_code})
    if request.method == 'POST' and form.is_valid():
        try:
            booking = review_booking(request.user, booking.pk, form.cleaned_data)
            return redirect('payment-page', pk=booking.pk)
        except BookingError as exc:
            messages.error(request, tr(exc.code))
    return render(request, 'checkout.html', {'booking': booking, 'event': booking.event, 'form': form, 'no_footer': True})


@login_required
def payment_page(request, pk):
    booking = get_object_or_404(Booking, pk=pk, user=request.user)
    expire_event(booking.event_id)
    booking.refresh_from_db()
    return render(request, 'payment.html', {'booking': booking, 'event': booking.event, 'no_footer': True})


@login_required
def success(request, pk):
    booking = get_object_or_404(Booking, pk=pk, user=request.user, status='paid')
    return render(request, 'success.html', {'booking': booking, 'event': booking.event, 'no_footer': True})


@login_required
@require_POST
def payment(request, pk):
    get_object_or_404(Booking, pk=pk, user=request.user)
    try:
        pay(request.user, pk, request.POST.get('outcome', 'approve'))
        messages.success(request, tr('success_intro'))
        return redirect('success', pk=pk)
    except BookingError as exc:
        messages.error(request, tr(exc.code))
        return redirect('payment-page', pk=pk)


@login_required
@require_POST
def cancel_booking(request, pk):
    get_object_or_404(Booking, pk=pk, user=request.user)
    try:
        cancel(request.user, pk)
    except BookingError as exc:
        messages.error(request, tr(exc.code))
    return redirect('wallet')


@login_required
def wallet(request):
    bookings = Booking.objects.filter(user=request.user).select_related('event').prefetch_related('items__seat', 'items__ticket')
    for event_id in bookings.filter(status='held').values_list('event_id', flat=True).distinct():
        expire_event(event_id)
    past = request.GET.get('tab') == 'past'
    bookings = bookings.filter(event__starts_at__lt=timezone.now()) if past else bookings.filter(event__starts_at__gte=timezone.now())
    return render(request, 'wallet.html', {'bookings': bookings, 'past': past})


@login_required
@require_POST
def favorite(request, pk):
    event = get_object_or_404(Event, pk=pk, published=True)
    obj, created = Favorite.objects.get_or_create(user=request.user, event=event)
    if not created:
        obj.delete()
    target = request.POST.get('next', '')
    if target and url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return redirect(target)
    return redirect('home')


@login_required
def qr(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk, item__booking__user=request.user, item__booking__status='paid')
    url = request.build_absolute_uri(reverse('scan', args=[ticket.pk]))
    response = HttpResponse(render_svg(url), content_type='image/svg+xml')
    response['Cache-Control'] = 'private, no-store'
    if request.GET.get('download') == '1':
        response['Content-Disposition'] = f'attachment; filename="ticket-{ticket.pk}.svg"'
    return response


@login_required
def calendar(request, pk):
    booking = get_object_or_404(Booking, pk=pk, user=request.user, status='paid')
    event = booking.event
    def escaped(value):
        return value.replace('\\', '\\\\').replace('\r', '').replace('\n', '\\n').replace(',', '\\,').replace(';', '\\;')
    from datetime import timezone as dt_timezone
    stamp = lambda d: d.astimezone(dt_timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//TicketFlow//UZ', 'BEGIN:VEVENT',
             f'UID:{booking.pk}@ticketflow', f'DTSTAMP:{stamp(timezone.now())}',
             f'DTSTART:{stamp(event.starts_at)}', f'DTEND:{stamp(event.starts_at + timedelta(hours=2))}',
             f'SUMMARY:{escaped(event.title)}', f'LOCATION:{escaped(event.venue)}', 'END:VEVENT', 'END:VCALENDAR', '']
    response = HttpResponse('\r\n'.join(lines), content_type='text/calendar; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="ticketflow.ics"'
    return response


@operator_required('booking.check_in_ticket')
def scan(request, pk):
    ticket = get_object_or_404(Ticket.objects.select_related('item__booking__event', 'item__seat'), pk=pk)
    if request.method == 'POST':
        try:
            ticket = check_in(ticket.pk, actor=request.user)
            messages.success(request, 'Kirish tasdiqlandi.')
        except BookingError as exc:
            messages.error(request, tr(exc.code))
    return render(request, 'scan.html', {'ticket': ticket})


def live(request):
    return JsonResponse({'status': 'ok', 'service': 'ticketflow'})


def ready(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        from django.core.cache import cache
        cache.set('readiness', 'ok', timeout=10)
        if cache.get('readiness') != 'ok':
            raise RuntimeError('cache unavailable')
    except Exception:
        return JsonResponse({'status': 'unavailable'}, status=503)
    return JsonResponse({'status': 'ok'})


@login_required
def profile(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    editing = request.GET.get('edit') == '1' or request.method == 'POST'
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, tr('profile_saved'))
        return redirect('profile')
    favorites = Event.objects.filter(favorite__user=request.user, published=True)
    return render(request, 'profile.html', {'form': form, 'editing': editing, 'favorites': favorites,
        'booking_count': Booking.objects.filter(user=request.user).count(),
        'ticket_count': Ticket.objects.filter(item__booking__user=request.user).count()})


def directory(request, kind):
    field = 'artist' if kind == 'artists' else 'venue'
    rows = Event.objects.filter(published=True, starts_at__gt=timezone.now()).exclude(**{field: ''}).values(field).annotate(count=Count('pk')).order_by(field)
    cards = []
    for row in rows:
        photo_field = 'artist_photo' if kind == 'artists' else 'venue_photo'
        sample = Event.objects.filter(published=True, starts_at__gt=timezone.now(), **{field: row[field]}).exclude(**{photo_field: ''}).first()
        cards.append({'name': row[field], 'count': row['count'], 'image': getattr(sample, photo_field, ''),
                      'filter': 'q' if field == 'artist' else 'venue'})
    return render(request, 'directory.html', {'cards': cards, 'kind': kind})


def information(request, section='help'):
    return render(request, 'information.html', {'section': section})


@require_POST
def subscribe(request):
    form = SubscriptionForm(request.POST)
    if form.is_valid():
        NewsletterSubscription.objects.get_or_create(email=form.cleaned_data['email'].lower(), defaults={'language': language()})
        messages.success(request, tr('newsletter_saved'))
    else:
        messages.error(request, tr('form_error'))
    return redirect('home')
