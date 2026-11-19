> Superseded by [17 November Figma integration verification](figma-verification.md). The earlier design and counts below are historical.

# Verification record — UFARM-3845

Date: 16 November 2026. Results below describe commands actually run, not assumed CI results.

## Latest revision: backend hardening and separate AQA suite

- **49 backend tests discovered; 48 passed, 1 PostgreSQL concurrency test skipped** on the available local runtime. Output: `.tmp/backend-v2-test.log`.
- Real HTTP customer/staff journey passed again after the schema, permission and payment-attempt changes.
- Added coverage for customer-scoped reservation idempotency, expired replay, hold limits, durable failed/abandoned payment attempts, attempt bursts, least-privilege roles, safe raster uploads, production poster delivery and safe favorite redirects.
- Fixed stale state on expired reservation replay, financial dashboard access for booking-only readers, production poster delivery, lost favorite filters and audit pagination filters.
- Separate `qa/` Playwright suite contains **17 browser acceptance scenarios**, including 27 route/viewport combinations, trace/video/screenshot capture and HTML/JSON reports.
- Executed `qa/run.py`: **BLOCKED before any browser tests ran**, due to Windows `PermissionError / WinError 5` while creating Playwright's driver pipe. Actual report: `.tmp/qa/20261116-161545-ea21/report.json`. No visual or browser pass is claimed.
- Rechecked Python syntax, JavaScript syntax and Docker Compose configuration. CI still has not run remotely.
- The new Figma Site reference could not be retrieved. Its visual match remains pending reference screenshots; the current light design is an interim revision.

The initial baseline below is retained as history; the counts above supersede its 31-test count.

## Passed locally

| Check | Result |
|---|---|
| Django system check | No issues |
| Initial migrations | Applied successfully |
| Migration drift | `makemigrations --check --dry-run`: no changes |
| Django unit/integration suite | 31 tests discovered; 30 passed, 1 skipped |
| Real payment HTTP | Signed request to separately running payment process; idempotent payment issued exactly one ticket |
| Customer + staff HTTP journey | Passed real sessions and CSRF, with no mocked payment transport |
| QR generation | Private SVG returned successfully using installed OpenCV backend |
| QR machine readability | Generated SVG modules reconstructed into a raster; OpenCV decoder recovered the exact check-in URL |
| JavaScript syntax | `node --check static/motion.js` and `static/figma.js` passed (legacy unused `app.js` removed) |
| Compose configuration | `docker compose config --quiet` passed with a local validation password |

The HTTP journey creates an event and seats through the custom Operations form, registers a customer through the website, searches, reserves, declines then approves payment, retries approval without issuing another ticket, retrieves wallet/QR/calendar, signs in as staff, checks in once, rejects duplicate check-in, and exports filtered CSV. The script hides its synthetic event and disables its synthetic accounts after completing the journey. It is meant for disposable demo data only.

Unit coverage includes cross-event seat rejection, duplicate seat requests, already-held seats, unpublished/past events, expiry and release, ownership checks, CSRF, late approval, payment retries, duplicate entry, API JWT registration/login, public availability, operations access, event inventory creation/editing, safe deletion and spreadsheet-formula escaping.

## Exact local runtime

- Python 3.12.10.
- Preinstalled Django **5.0.6**, DRF/SimpleJWT and SQLite. This differs from the project's intended Django **5.2.x** dependency range.
- Internet dependency installation was unavailable (`PIP_NO_INDEX=1`, external HTTP requests refused). No network or permission controls were disabled.
- A workspace-local `.tmp/verification_settings.py` imported `config.settings` and removed WhiteNoise middleware because that package was unavailable. Django runserver served local static assets instead.
- OpenCV 4.10 was available, so the optional real QR encoder was used. The preferred `qrcode` backend was not installed locally and has not been exercised here.
- Web and payment were run as separate local processes on 127.0.0.1 ports 8000 and 8001. This was an actual HTTP integration, not a Django test-client substitute.

These results establish local functional behavior; they do **not** establish the target dependency/container stack or production readiness.

## Blocked or not executed

1. **PostgreSQL concurrency:** a separate cluster was initialized under `.tmp/pg-test`, using port 55432 rather than the existing machine database. PostgreSQL startup failed at Windows restricted-token creation. No existing databases or services were modified. The row-lock test was skipped under SQLite.
2. **Docker build/runtime:** Docker API access failed (initially engine unavailable, later named-pipe permission denied). Compose syntax was checked, but no container image/build/runtime pass is claimed.
3. **Browser visual/E2E:** Playwright failed creating a Windows named pipe. Selenium with a matching cached Chromium/ChromeDriver also failed to start a browser session. No visual screenshots, responsive render inspection or browser JavaScript execution pass is claimed.
4. **Live competitor audit:** HTTP requests to all five supplied sites were refused. The evidence limits are recorded in `frontend-review.md`.
5. **Remote CI:** workflow authored, not triggered in this environment. The folder was not an initialized Git repository and no remote push or deployment occurred.

## Target verification commands

On a host with working Docker and package access:

```powershell
Copy-Item .env.example .env
docker compose up --build -d
docker compose exec web python manage.py seed_demo
docker compose exec web python manage.py test booking payment_service --verbosity 2
docker compose exec web python manage.py createsuperuser
```

For a disposable local database with dependencies installed and both servers running:

```powershell
python scripts/http_smoke.py --allow-demo-data
python -m pip install playwright
python -m playwright install chromium
python scripts/browser_smoke.py
```

The CI workflow performs PostgreSQL tests, HTTP integration, browser smoke/screenshots and Docker image build. Review those results before merging/deploying or claiming the target stack is fully verified.
