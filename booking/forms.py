from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.utils import timezone
from .models import Event


def _email_in_use(email, exclude_pk=None):
    users = get_user_model().objects.filter(email__iexact=email)
    return users.exclude(pk=exclude_pk).exists() if exclude_pk else users.exists()


class RegisterForm(UserCreationForm):
    """Sign-up form shared by the website and the API. Email stays optional, but a
    given address can belong to one account only (case-insensitive)."""
    email = forms.EmailField(required=False, max_length=254)

    class Meta(UserCreationForm.Meta):
        fields = ('username', 'email')

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if email and _email_in_use(email):
            raise forms.ValidationError('Bu email allaqachon ro‘yxatdan o‘tgan.', code='email_taken')
        return email


class DiscoveryForm(forms.Form):
    q = forms.CharField(required=False, max_length=100)
    category = forms.ChoiceField(required=False, choices=[('', 'Barchasi'), ('music', 'Konsert'), ('theatre', 'Teatr'), ('sport', 'Sport'), ('tech', 'Texnologiya'), ('festival', 'Festival'), ('cinema', 'Kino')])
    venue = forms.CharField(required=False, max_length=120)
    date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    max_price = forms.IntegerField(required=False, min_value=0)
    sort = forms.ChoiceField(required=False, choices=[('', 'Sana bo‘yicha'), ('price', 'Arzonidan')])


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['title', 'category', 'venue', 'starts_at', 'description', 'artist', 'artist_photo', 'venue_photo', 'city', 'title_ru', 'title_en', 'description_ru', 'description_en', 'reference_image', 'poster', 'artwork', 'refundable', 'published']
        widgets = {'starts_at': forms.DateTimeInput(format='%Y-%m-%dT%H:%M', attrs={'type': 'datetime-local'}),
                   'description': forms.Textarea(attrs={'rows': 5})}
        labels = {'title': 'Tadbir nomi', 'category': 'Kategoriya', 'venue': 'Joy nomi',
                  'starts_at': 'Boshlanish vaqti (Toshkent)', 'description': 'Tavsif',
                  'artwork': 'Poster uslubi', 'refundable': 'Qaytarish mumkin', 'published': 'Saytda e’lon qilish'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['city'].required = False

    def clean_city(self):
        return self.cleaned_data.get('city') or 'Toshkent'

    def clean_poster(self):
        image = self.cleaned_data.get('poster')
        if image and hasattr(image, 'content_type'):
            if image.size > 5 * 1024 * 1024:
                raise forms.ValidationError('Rasm hajmi 5 MB dan oshmasin.')
            if image.image.format not in ('JPEG', 'PNG', 'WEBP'):
                raise forms.ValidationError('JPEG, PNG yoki WebP rasm yuklang.')
            if image.image.width * image.image.height > 20000000:
                raise forms.ValidationError('Rasm 20 megapikseldan kichik bo‘lsin.')
        return image


class NewEventForm(EventForm):
    rows = forms.IntegerField(min_value=1, max_value=12, initial=3, label='Har bir sektorda qatorlar soni')
    seats_per_row = forms.IntegerField(min_value=1, max_value=20, initial=8, label='Bir qatorda o‘rindiqlar')
    price = forms.IntegerField(min_value=1000, max_value=100000000, initial=100000, label='Standard narx (UZS)')
    vip_price = forms.IntegerField(min_value=1000, max_value=100000000, initial=200000, label='VIP narx (UZS)')

    def clean_starts_at(self):
        value = self.cleaned_data['starts_at']
        if value <= timezone.now():
            raise forms.ValidationError('Kelajakdagi vaqtni tanlang.')
        return value


class CheckoutForm(forms.Form):
    contact_name = forms.CharField(max_length=120, min_length=2)
    contact_email = forms.EmailField()
    contact_phone = forms.RegexField(r'^\+?[0-9 ()-]{7,20}$', required=False, max_length=20)
    promo_code = forms.CharField(required=False, max_length=32)


class ProfileForm(forms.ModelForm):
    class Meta:
        model = get_user_model()
        fields = ['first_name', 'last_name', 'email']

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if email and _email_in_use(email, self.instance.pk):
            raise forms.ValidationError('Bu email boshqa hisobda ishlatilgan.', code='email_taken')
        return email


class SubscriptionForm(forms.Form):
    email = forms.EmailField()
