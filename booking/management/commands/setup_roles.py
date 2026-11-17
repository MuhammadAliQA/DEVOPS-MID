from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

ROLES = {
    'Event managers': ['view_event', 'add_event', 'change_event', 'delete_event'],
    'Booking operators': ['view_booking', 'change_booking', 'view_payment', 'view_paymentattempt'],
    'Gate staff': ['check_in_ticket'],
    'Auditors': ['view_auditlog'],
}


class Command(BaseCommand):
    help = 'Create least-privilege platform groups. Does not assign users.'

    def handle(self, *args, **options):
        for name, permissions in ROLES.items():
            group, _ = Group.objects.get_or_create(name=name)
            group.permissions.set(Permission.objects.filter(content_type__app_label='booking', codename__in=permissions))
        self.stdout.write('Platform roles configured. Assign groups to staff accounts in technical admin.')
