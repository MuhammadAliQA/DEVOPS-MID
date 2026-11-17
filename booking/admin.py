from django import forms
from django.contrib import admin
from django.contrib.admin.utils import unquote
from django.db import models, transaction
from django.db.models import Count
from django.utils.html import format_html
from .forms import EventForm, NewEventForm
from .models import AuditLog, Booking, Event, NewsletterSubscription, Payment, PaymentAttempt, Seat, Ticket
from .services import audit


class SeatInline(admin.TabularInline):
    model = Seat
    extra = 0
    fields = readonly_fields = ['sector', 'row', 'number', 'price', 'availability']
    can_delete = False
    classes = ['collapse']

    @admin.display(description='Holat')
    def availability(self, obj): return 'Band' if obj.reservation_id else 'Bo‘sh'
    def has_view_permission(self, request, obj=None): return request.user.has_perm('booking.view_event')
    def has_add_permission(self, request, obj=None): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    # Operations uses one datetime-local input; admin's default SplitDateTimeField
    # otherwise conflicts with EventForm's single-value widget.
    formfield_overrides = {models.DateTimeField: {'form_class': forms.DateTimeField,
        'widget': forms.DateTimeInput(format='%Y-%m-%dT%H:%M', attrs={'type': 'datetime-local'})}}
    list_display = ['title', 'category', 'venue', 'starts_at', 'publication', 'seat_count']
    list_filter = ['published', 'category', 'city', 'refundable']
    search_fields = ['title', 'title_ru', 'title_en', 'artist', 'venue']
    date_hierarchy = 'starts_at'
    list_per_page = 25
    inlines = [SeatInline]
    actions = None
    save_on_top = True
    readonly_fields = ['poster_preview']
    fieldsets = [
        ('Tadbir', {'fields': ('title', ('category', 'artist'), ('venue', 'city'), 'starts_at', 'description')}),
        ('Rasmlar', {'description': 'Afisha, san’atkor portreti va maydon rasmi alohida ishlatiladi.',
                    'fields': ('poster_preview', 'poster', 'reference_image', 'artist_photo', 'venue_photo', 'artwork')}),
        ('Tarjimalar · RU / EN', {'classes': ('collapse',), 'fields': ('title_ru', 'description_ru', 'title_en', 'description_en')}),
        ('Nashr va shartlar', {'fields': ('published', 'refundable')}),
    ]

    def get_form(self, request, obj=None, **kwargs):
        kwargs['form'] = EventForm if obj else NewEventForm
        return super().get_form(request, obj, **kwargs)

    def get_fieldsets(self, request, obj=None):
        result = list(self.fieldsets)
        if obj is None:
            result.append(('Boshlang‘ich inventar · A va VIP', {'fields': (('rows', 'seats_per_row'), ('price', 'vip_price'))}))
        return result

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(inventory_count=Count('seats'))

    @admin.display(description='O‘rindiqlar', ordering='inventory_count')
    def seat_count(self, obj): return obj.inventory_count

    @admin.display(description='Nashr', boolean=True)
    def publication(self, obj): return obj.published

    @admin.display(description='Afisha')
    def poster_preview(self, obj):
        if not obj or not obj.pk: return 'Saqlangandan keyin ko‘rinadi'
        return format_html('<img class="control-poster" src="{}" alt="{}">', obj.image_url, obj.title)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not change:
            data = form.cleaned_data
            Seat.objects.bulk_create([
                Seat(event=obj, sector=sector, row=chr(65 + row), number=number,
                     price=data['vip_price'] if sector == 'VIP' else data['price'])
                for sector in ('A', 'VIP') for row in range(data['rows']) for number in range(1, data['seats_per_row'] + 1)
            ])
        audit(request.user, 'event.updated' if change else 'event.created', obj.pk, title=obj.title, source='django_admin')

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        # Same event lock used by reserve/pay/operations, held through all form saves.
        with transaction.atomic():
            if request.method == 'POST' and object_id:
                obj = self.get_object(request, unquote(object_id))
                if obj: Event.objects.select_for_update().get(pk=obj.pk)
            return super().changeform_view(request, object_id, form_url, extra_context)

    def has_delete_permission(self, request, obj=None):
        return super().has_delete_permission(request, obj) and (obj is None or not Booking.objects.filter(event=obj).exists())

    def delete_view(self, request, object_id, extra_context=None):
        with transaction.atomic():
            if request.method == 'POST':
                obj = self.get_object(request, unquote(object_id))
                if obj: Event.objects.select_for_update().get(pk=obj.pk)
            return super().delete_view(request, object_id, extra_context)

    def delete_model(self, request, obj):
        audit(request.user, 'event.deleted', obj.pk, title=obj.title, source='django_admin')
        super().delete_model(request, obj)


class ReadOnlyAdmin(admin.ModelAdmin):
    list_per_page = 25
    actions = None
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False


@admin.register(Booking)
class BookingAdmin(ReadOnlyAdmin):
    list_display = ['id', 'user', 'event', 'status', 'total', 'expires_at']
    list_filter = ['status']
    search_fields = ['user__username', 'event__title', 'contact_email', 'id']
    list_select_related = ['user', 'event']
    date_hierarchy = 'created_at'


@admin.register(Payment)
class PaymentAdmin(ReadOnlyAdmin):
    list_display = ['reference', 'booking', 'amount', 'created_at']
    search_fields = ['reference', 'booking__user__username', 'booking__event__title']
    list_select_related = ['booking']
    date_hierarchy = 'created_at'


@admin.register(Ticket)
class TicketAdmin(ReadOnlyAdmin):
    list_display = ['id', 'event_title', 'seat_label', 'checked_in_at']
    list_filter = [('checked_in_at', admin.EmptyFieldListFilter)]
    search_fields = ['id', 'item__booking__user__username', 'item__booking__event__title']
    list_select_related = ['item__booking__event', 'item__seat']
    @admin.display(description='Tadbir')
    def event_title(self, obj): return obj.item.booking.event.title
    @admin.display(description='O‘rindiq')
    def seat_label(self, obj): return str(obj.item.seat)


@admin.register(PaymentAttempt)
class PaymentAttemptAdmin(ReadOnlyAdmin):
    list_display = ['id', 'booking', 'status', 'error_code', 'created_at', 'finished_at']
    list_filter = ['status', 'error_code']
    search_fields = ['id', 'booking__user__username', 'booking__event__title']
    list_select_related = ['booking']


@admin.register(AuditLog)
class AuditLogAdmin(ReadOnlyAdmin):
    list_display = ['created_at', 'actor', 'action', 'target']
    list_filter = ['action']
    search_fields = ['target', 'actor__username']
    list_select_related = ['actor']
    date_hierarchy = 'created_at'


@admin.register(NewsletterSubscription)
class NewsletterAdmin(ReadOnlyAdmin):
    list_display = ['email', 'language', 'created_at']
    list_filter = ['language']
    search_fields = ['email']
