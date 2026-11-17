"""Run inside the web container to verify health and actual production asset serving."""
from urllib.request import urlopen

base = 'http://127.0.0.1:8000'
for path in ['/health/live/', '/health/ready/', '/admin/login/']:
    with urlopen(base + path, timeout=10) as response:
        assert response.status == 200, path
for path, content_type in [('/static/admin/control.css', 'text/css'), ('/static/admin/css/base.css', 'text/css'),
                           ('/static/operations-control.css', 'text/css'), ('/static/vendor/anime.umd.min.js', 'javascript')]:
    with urlopen(base + path, timeout=10) as response:
        assert response.status == 200 and content_type in response.headers.get('Content-Type', ''), path
        assert len(response.read()) > 100, path
print('PASS: health, admin login, Django admin/custom CSS and Anime.js served over HTTP')
