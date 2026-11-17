from datetime import timedelta
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from booking.models import Event, Seat


class Command(BaseCommand):
    help = 'Create fictional demo events and seats, without creating accounts.'

    @transaction.atomic
    def handle(self, *args, **options):
        examples = [
            ('Tashkent Afterglow', 'music', 'Humo Arena', 'Shahar ritmi. Jonli musiqa, yorug‘lik va unutilmas kecha.', 150000),
            ('Ipak yo‘li simfoniyasi', 'theatre', 'Alisher Navoiy teatri', 'Klassik ohanglar va zamonaviy sahna bir kechada.', 80000),
            ('Derby Night', 'sport', 'Milliy stadion', 'Tribuna energiyasini his qiling. Katta futbol oqshomi.', 60000),
            ('Build Tomorrow', 'tech', 'Uzexpocentre', 'Dasturchilar, muhandislar va yangi g‘oyalar uchrashuvi.', 100000),
            ('Jazz under the Stars', 'music', 'Turkiston saroyi', 'Shoshilmaydigan oqshom. Jazz va jonli improvizatsiya.', 120000),
            ('Sahna: yangi hikoya', 'theatre', 'Ilhom teatri', 'Yaqin sahna, katta tuyg‘ular. Zamonaviy teatr tajribasi.', 70000),
        ]
        photos = ['https://images.unsplash.com/photo-1459749411175-04bf5292ceea?auto=format&fit=crop&w=1600&q=85', 'https://images.unsplash.com/photo-1470229722913-7c0e2dbbafd3?auto=format&fit=crop&w=1200&q=80', 'https://images.unsplash.com/photo-1514525253161-7a46d19cd819?auto=format&fit=crop&w=1200&q=80', 'https://images.unsplash.com/photo-1506157786151-b8491531f063?auto=format&fit=crop&w=1200&q=80', 'https://images.unsplash.com/photo-1603910234616-3b5f4a6be2b4?auto=format&fit=crop&w=1200&q=80', 'https://images.unsplash.com/photo-1565035010268-a3816f98589a?auto=format&fit=crop&w=1200&q=80', 'https://images.unsplash.com/photo-1497911270199-1c552ee64aa4?auto=format&fit=crop&w=1200&q=80', 'https://images.unsplash.com/photo-1563841930606-67e2bce48b78?auto=format&fit=crop&w=1200&q=80']
        for index, (title, category, venue, description, price) in enumerate(examples):
            event, created = Event.objects.get_or_create(title=title, defaults={
                'category': category, 'venue': venue, 'description': description,
                'starts_at': (timezone.now() + timedelta(days=7 + index * 3)).replace(hour=14, minute=0, second=0, microsecond=0),
                'reference_image': photos[index], 'artist': 'TICKETLY Demo', 'city': 'Toshkent',
                'published': True, 'artwork': category, 'refundable': index % 3 != 2})
            if not created and not event.reference_image and not event.poster:
                event.reference_image = photos[index]
                event.artist = event.artist or 'TICKETLY Demo'
                event.save(update_fields=['reference_image', 'artist'])
            if created:
                Seat.objects.bulk_create([Seat(event=event, sector=sector, row=row, number=number,
                                               price=price * (2 if sector == 'VIP' else 1))
                                          for sector in ['A', 'VIP'] for row in ['A', 'B', 'C'] for number in range(1, 9)])
        self.stdout.write(self.style.SUCCESS('Demo events ready. All events are fictional.'))
