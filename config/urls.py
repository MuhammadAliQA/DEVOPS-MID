from django.contrib import admin
from django.contrib.auth import views as auth
from django.urls import include, path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from booking import api, operations, views

urlpatterns = [
    path('', views.home, name='home'),
    path('events/', views.home, {'listing': True}, name='events'),
    path('artists/', views.directory, {'kind': 'artists'}, name='artists'),
    path('venues/', views.directory, {'kind': 'venues'}, name='venues'),
    path('profile/', views.profile, name='profile'),
    path('accounts/password/change/', auth.PasswordChangeView.as_view(
        template_name='registration/password_change.html',
        success_url='/accounts/password/changed/'), name='password_change'),
    path('accounts/password/changed/', auth.PasswordChangeDoneView.as_view(
        template_name='registration/password_changed.html'), name='password_change_done'),
    path('help/', views.information, name='help'),
    path('privacy/', views.information, {'section': 'privacy'}, name='privacy'),
    path('terms/', views.information, {'section': 'terms'}, name='terms'),
    path('subscribe/', views.subscribe, name='subscribe'),
    path('i18n/', include('django.conf.urls.i18n')), 
    path('events/<int:pk>/', views.detail, name='detail'),
    path('events/<int:pk>/poster/', views.poster, name='poster'),
    path('events/<int:pk>/seats/', views.seat_selection, name='seats'),
    path('events/<int:pk>/book/', views.book, name='book'),
    path('events/<int:pk>/favorite/', views.favorite, name='favorite'),
    path('bookings/<uuid:pk>/', views.checkout, name='checkout'),
    path('bookings/<uuid:pk>/payment/', views.payment_page, name='payment-page'),
    path('bookings/<uuid:pk>/success/', views.success, name='success'),
    path('bookings/<uuid:pk>/pay/', views.payment, name='payment'),
    path('bookings/<uuid:pk>/cancel/', views.cancel_booking, name='cancel'),
    path('bookings/<uuid:pk>/refund/', views.refund_booking, name='refund'),
    path('bookings/<uuid:pk>/calendar/', views.calendar, name='calendar'),
    path('tickets/', views.wallet, name='wallet'),
    path('tickets/<uuid:pk>/qr/', views.qr, name='qr'),
    path('staff/scan/<uuid:pk>/', views.scan, name='scan'),
    path('accounts/register/', views.register, name='register'),
    path('accounts/login/', auth.LoginView.as_view(), name='login'),
    path('accounts/logout/', auth.LogoutView.as_view(), name='logout'),
    path('admin/', admin.site.urls),
    path('operations/', operations.dashboard, name='ops-dashboard'),
    path('operations/events/', operations.events, name='ops-events'),
    path('operations/events/new/', operations.event_edit, name='ops-event-new'),
    path('operations/events/<int:pk>/', operations.event_edit, name='ops-event-edit'),
    path('operations/events/<int:pk>/delete/', operations.event_delete, name='ops-event-delete'),
    path('operations/bookings/', operations.bookings, name='ops-bookings'),
    path('operations/bookings/<uuid:pk>/cancel/', operations.cancel_hold, name='ops-cancel'),
    path('operations/export/', operations.export, name='ops-export'),
    path('operations/activity/', operations.activity, name='ops-activity'),
    path('operations/payments/', operations.payment_attempts, name='ops-payments'),
    path('operations/gate/', operations.gate, name='ops-gate'),
    path('api/register/', api.register),
    path('api/token/', TokenObtainPairView.as_view()),
    path('api/token/refresh/', TokenRefreshView.as_view()),
    path('api/events/', api.events),
    path('api/events/<int:pk>/seats/', api.seats),
    path('api/bookings/', api.bookings),
    path('api/bookings/<uuid:pk>/', api.booking_detail),
    path('api/bookings/<uuid:pk>/pay/', api.payment),
    path('api/bookings/<uuid:pk>/checkout/', api.checkout),
    path('api/bookings/<uuid:pk>/cancel/', api.cancel_reservation),
    path('api/bookings/<uuid:pk>/refund/', api.refund_booking),
    path('api/events/<int:pk>/', api.event_detail),
    path('health/live/', views.live),
    path('health/ready/', views.ready),
]

from django.conf import settings
from django.conf.urls.static import static
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
