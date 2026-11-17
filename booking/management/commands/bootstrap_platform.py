from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Apply schema and configure platform roles. Never creates passwords, users or demo events.'

    def handle(self, *args, **options):
        call_command('migrate', interactive=False)
        call_command('setup_roles')
