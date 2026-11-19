from django.contrib.admin.apps import AdminConfig


class TicketlyAdminConfig(AdminConfig):
    """
    Custom admin app config.
    - name='booking.admin_apps' is NOT set here; we keep the standard
      django.contrib.admin in INSTALLED_APPS so its label='admin' is registered.
    - We override default_site so the admin UI uses TicketlyAdminSite.
    - All model registrations happen in ready() to avoid AppRegistryNotReady.
    """
    default_site = 'booking.admin_site.TicketlyAdminSite'

    def ready(self):
        """Register all admin model classes after the app registry is fully loaded."""
        from django.contrib import admin
        from .models import (
            AuditLog, Booking, Event, NewsletterSubscription,
            Payment, PaymentAttempt, Seat, Ticket,
        )
        from .forms import EventForm, NewEventForm
        from .services import audit as audit_fn
        from .admin import (
            build_event_admin, build_booking_admin, build_payment_admin,
            build_ticket_admin, build_payment_attempt_admin,
            build_audit_log_admin, build_newsletter_admin,
        )

        site = admin.site

        site.register(Event,
            build_event_admin(Event, Seat, Booking, EventForm, NewEventForm, audit_fn))
        site.register(Booking, build_booking_admin())
        site.register(Payment, build_payment_admin())
        site.register(Ticket, build_ticket_admin())
        site.register(PaymentAttempt, build_payment_attempt_admin())
        site.register(AuditLog, build_audit_log_admin())
        site.register(NewsletterSubscription, build_newsletter_admin())
