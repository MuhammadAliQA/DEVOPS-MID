from django.contrib.admin.apps import AdminConfig


class TicketlyAdminConfig(AdminConfig):
    default_site = 'booking.admin_site.TicketlyAdminSite'
