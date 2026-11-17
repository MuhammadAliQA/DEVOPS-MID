"""CI-only browser verification. Run against a seeded, disposable test database."""
import os
import sys
import time
from pathlib import Path
from urllib.request import urlopen
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from django.contrib.auth.models import User, Permission
from django.test import Client
from playwright.sync_api import sync_playwright

output = Path('.tmp/screenshots')
output.mkdir(parents=True, exist_ok=True)
staff, _ = User.objects.get_or_create(username='ci-browser-operator', defaults={'is_staff': True})
staff.user_permissions.set(Permission.objects.filter(content_type__app_label='booking'))
client = Client()
client.force_login(staff)
cookie = client.cookies['sessionid'].value
for attempt in range(30):
    try:
        with urlopen('http://127.0.0.1:8000/health/ready/', timeout=1) as response:
            assert response.status == 200
        break
    except OSError:
        if attempt == 29:
            raise
        time.sleep(.2)
with sync_playwright() as playwright:
    browser = playwright.chromium.launch()
    page = browser.new_page(viewport={'width': 1440, 'height': 1000}, locale='uz-UZ')
    errors = []
    page.on('pageerror', lambda exc: errors.append(str(exc)))
    page.goto('http://127.0.0.1:8000/', wait_until='networkidle')
    assert page.locator('.event-card').count() >= 4
    page.screenshot(path=str(output / 'catalog-desktop.png'), full_page=True)
    page.context.add_cookies([{'name': 'sessionid', 'value': cookie, 'domain': '127.0.0.1', 'path': '/'}])
    page.locator('.event-card h3 a').first.click()
    page.locator('a[href$="/seats/"]').click()
    page.locator('input[name=seats]:not([disabled])').first.check()
    assert '1' in page.locator('#selection-heading').inner_text()
    page.select_option('#sector-filter', 'VIP')
    assert page.locator('[data-sector="VIP"]').is_visible()
    page.screenshot(path=str(output / 'seats-desktop.png'), full_page=True)
    page.context.add_cookies([{'name': 'sessionid', 'value': cookie, 'domain': '127.0.0.1', 'path': '/'}])
    for width in [1440, 768, 390]:
        page.set_viewport_size({'width': width, 'height': 1000})
        for name, route in [('catalog', '/'), ('operations', '/operations/'), ('events', '/operations/events/'), ('gate', '/operations/gate/')]:
            page.goto('http://127.0.0.1:8000' + route, wait_until='networkidle')
            assert page.locator('body').is_visible()
            assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), (route, width)
            page.screenshot(path=str(output / f'{name}-{width}.png'), full_page=True)
    assert not errors, errors
    browser.close()
print('Browser routes, sector interaction and responsive overflow: PASS')
