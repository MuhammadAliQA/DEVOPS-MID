from django import template
from django.utils.safestring import mark_safe
from booking.translations import tr

register = template.Library()


@register.simple_tag
def t(key, **values):
    return tr(key, **values)


@register.simple_tag
def category(value):
    return tr('cat_' + value)


@register.simple_tag
def booking_status(value):
    return tr('status_' + value)


@register.filter
def money(value):
    return f'{int(value or 0):,}'.replace(',', ' ')


ICONS = {
    'arrow': '<path d="M5 12h14m-6-6 6 6-6 6"/>',
    'back': '<path d="M19 12H5m6-6-6 6 6 6"/>',
    'calendar': '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 11h18m-13 4h2m4 0h2"/>',
    'pin': '<path d="M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="2.5"/>',
    'search': '<circle cx="10.5" cy="10.5" r="7"/><path d="m16 16 5 5"/>',
    'heart': '<path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8L12 21l8.8-8.6a5.5 5.5 0 0 0 0-7.8Z"/>',
    'ticket': '<path d="M3 7a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v3a2 2 0 0 0 0 4v3a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-3a2 2 0 0 0 0-4Z"/><path d="M15 5v2m0 3v2m0 3v4"/>',
    'user': '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="8" r="3"/><path d="M5 19c1-6 13-6 14 0"/>',
    'users': '<circle cx="9" cy="7" r="3"/><path d="M3 21v-3a6 6 0 0 1 12 0v3M16 4a3 3 0 0 1 0 6m3 11v-3a5 5 0 0 0-2-4"/>',
    'clock': '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    'shield': '<path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6Z"/><path d="m8 12 3 3 5-6"/>',
    'check': '<path d="m5 12 4 4L19 6"/>',
    'x': '<path d="m6 6 12 12M6 18 18 6"/>',
    'menu': '<path d="M4 6h16M4 12h16M4 18h16"/>',
    'music': '<path d="M9 18V5l12-2v13M9 9l12-2"/><ellipse cx="6" cy="18" rx="3" ry="3"/><ellipse cx="18" cy="16" rx="3" ry="3"/>',
    'sparkles': '<path d="m12 3 2.6 6.4L21 12l-6.4 2.6L12 21l-2.6-6.4L3 12l6.4-2.6ZM20 2v4m-2-2h4"/>',
    'zap': '<path d="m13 2-9 12h7l-1 8 10-12h-7Z"/>',
    'down': '<path d="m6 9 6 6 6-6"/>',
    'download': '<path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5"/>',
    'wallet': '<rect x="3" y="5" width="18" height="15" rx="2"/><path d="M3 9h18m-6 5h6"/>',
}


@register.simple_tag
def icon(name):
    return mark_safe('<svg class="icon" viewBox="0 0 24 24" aria-hidden="true">' + ICONS.get(name, ICONS['ticket']) + '</svg>')
