import uuid
from django.conf import settings
from django.db import models
from django.db.models import Q


class Event(models.Model):
    title = models.CharField(max_length=160)
    category = models.CharField(max_length=20, choices=[('music', 'Konsert'), ('theatre', 'Teatr'), ('sport', 'Sport'), ('tech', 'Texnologiya'), ('festival', 'Festival'), ('cinema', 'Kino')])
    venue = models.CharField(max_length=120)
    starts_at = models.DateTimeField()
    description = models.TextField()
    poster = models.ImageField(upload_to='posters/%Y/%m/', blank=True)
    reference_image = models.URLField(max_length=800, blank=True)
    artist = models.CharField(max_length=120, blank=True)
    artist_photo = models.URLField(max_length=800, blank=True, help_text='Artist portrait URL, not an event poster.')
    venue_photo = models.URLField(max_length=800, blank=True, help_text='Photo of this venue, not an event poster.')
    city = models.CharField(max_length=80, default='Toshkent')
    title_ru = models.CharField(max_length=160, blank=True)
    title_en = models.CharField(max_length=160, blank=True)
    description_ru = models.TextField(blank=True)
    description_en = models.TextField(blank=True)
    published = models.BooleanField(default=False)
    refundable = models.BooleanField(default=True)
    artwork = models.CharField(max_length=20, default='music', choices=[('music', 'Music'), ('theatre', 'Theatre'), ('sport', 'Sport'), ('tech', 'Tech')])

    class Meta:
        ordering = ['starts_at']
        permissions = [('check_in_ticket', 'Can validate tickets at the gate')]
        indexes = [models.Index(fields=['published', 'starts_at'], name='event_discovery_idx')]

    def __str__(self):
        return self.title

    @property
    def display_title(self):
        from django.utils.translation import get_language
        return getattr(self, 'title_' + (get_language() or 'uz')[:2], '') or self.title

    @property
    def display_description(self):
        from django.utils.translation import get_language
        return getattr(self, 'description_' + (get_language() or 'uz')[:2], '') or self.description

    @property
    def image_url(self):
        from django.urls import reverse
        from django.templatetags.static import static
        return reverse('poster', args=[self.pk]) if self.poster else self.reference_image or static('figma-favicon.png')


class Booking(models.Model):
    class Status(models.TextChoices):
        HELD = 'held', 'Bron qilingan'
        PAID = 'paid', "To‘langan"
        EXPIRED = 'expired', 'Vaqti tugagan'
        CANCELLED = 'cancelled', 'Bekor qilingan'
        REFUNDED = 'refunded', 'Qaytarilgan'
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    event = models.ForeignKey(Event, on_delete=models.PROTECT)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.HELD)
    total = models.PositiveIntegerField()
    expires_at = models.DateTimeField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    idempotency_key = models.UUIDField(null=True, blank=True, editable=False)
    contact_name = models.CharField(max_length=120, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    discount = models.PositiveIntegerField(default=0)
    promo_code = models.CharField(max_length=32, blank=True)
    refunded_at = models.DateTimeField(null=True, blank=True)

    @property
    def subtotal(self):
        return self.total + self.discount

    class Meta:
        ordering = ['-created_at']
        constraints = [models.UniqueConstraint(fields=['user', 'idempotency_key'], name='unique_user_reservation_key')]
        indexes = [models.Index(fields=['status', 'expires_at'], name='booking_expiry_idx')]


class Seat(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='seats')
    sector = models.CharField(max_length=20, default='A')
    row = models.CharField(max_length=4)
    number = models.PositiveSmallIntegerField()
    price = models.PositiveIntegerField(help_text='UZS, no hidden fees')
    reservation = models.ForeignKey(Booking, null=True, blank=True, on_delete=models.PROTECT, related_name='reserved_seats')

    class Meta:
        ordering = ['sector', 'row', 'number']
        constraints = [models.UniqueConstraint(fields=['event', 'sector', 'row', 'number'], name='unique_event_seat'),
                       models.CheckConstraint(check=Q(price__gt=0), name='positive_seat_price')]

    def __str__(self):
        return f'{self.sector} / {self.row}{self.number}'


class BookingSeat(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='items')
    seat = models.ForeignKey(Seat, on_delete=models.PROTECT)
    price = models.PositiveIntegerField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=['booking', 'seat'], name='unique_booking_item')]


class Payment(models.Model):
    booking = models.OneToOneField(Booking, on_delete=models.PROTECT, related_name='payment')
    reference = models.CharField(max_length=64, unique=True)
    amount = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)


class Ticket(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item = models.OneToOneField(BookingSeat, on_delete=models.PROTECT, related_name='ticket')
    checked_in_at = models.DateTimeField(null=True, blank=True)


class Favorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'event'], name='unique_favorite')]


class PaymentAttempt(models.Model):
    class Status(models.TextChoices):
        STARTED = 'started', 'Processing'
        APPROVED = 'approved', 'Approved'
        FAILED = 'failed', 'Failed'
        ABANDONED = 'abandoned', 'Reservation no longer active'
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking = models.ForeignKey(Booking, on_delete=models.PROTECT, related_name='payment_attempts')
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.STARTED)
    error_code = models.CharField(max_length=40, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']


class AuditLog(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=50, db_index=True)
    target = models.CharField(max_length=80)
    details = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at', '-pk']


class NewsletterSubscription(models.Model):
    email = models.EmailField(unique=True)
    language = models.CharField(max_length=2, default='uz')
    created_at = models.DateTimeField(auto_now_add=True)
