from django.contrib.admin import AdminSite
from django.db.models import Sum
from django.utils import timezone


class TicketlyAdminSite(AdminSite):
    site_header = 'TICKETLY Control'
    site_title = 'TICKETLY Control'
    index_title = 'Platform boshqaruvi'
    index_template = 'admin/control_index.html'

    def index(self, request, extra_context=None):
        from .models import Booking, Event, Payment, Ticket
        cards = []
        if request.user.has_perm('booking.view_event'):
            cards.append({'label': 'Yaqin tadbirlar', 'value': Event.objects.filter(published=True, starts_at__gt=timezone.now()).count(), 'url': 'admin:booking_event_changelist', 'detail': 'Faol afisha'})
        if request.user.has_perm('booking.view_booking'):
            cards.append({'label': 'Faol bronlar', 'value': Booking.objects.filter(status='held', expires_at__gt=timezone.now()).count(), 'url': 'admin:booking_booking_changelist', 'detail': 'Muddati tugamagan'})
        if request.user.has_perm('booking.view_payment'):
            cards.append({'label': 'Demo tushum', 'value': Payment.objects.exclude(booking__status='refunded').aggregate(total=Sum('amount'))['total'] or 0, 'url': 'admin:booking_payment_changelist', 'detail': 'UZS · haqiqiy pul emas'})
        if request.user.has_perm('booking.view_ticket'):
            cards.append({'label': 'QR chiptalar', 'value': Ticket.objects.filter(item__booking__status='paid').count(), 'url': 'admin:booking_ticket_changelist', 'detail': 'Berilgan chiptalar'})
        return super().index(request, {**(extra_context or {}), 'control_cards': cards})
