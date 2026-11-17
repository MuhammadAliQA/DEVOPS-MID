# TicketFlow Playwright AQA

Separate browser acceptance suite for UFARM-3845. It drives the actual Django web application and payment simulator, with real browser sessions, CSRF, persisted state and HTTP payment calls.

## Run

From the repository root, with Python 3.12:

```powershell
python -m pip install -r qa/requirements.txt
python -m playwright install chromium
python qa/run.py
```

The runner starts and stops its own web/payment processes on **8990 / 8991**, creates a new SQLite database and upload directory under `.tmp/qa/<run-id>/`, and never points at the normal `db.sqlite3` or existing PostgreSQL databases. Do not manually start the development servers for this suite. Ports 8990 and 8991 must be free.

Specific scenario or alternate browser:

```powershell
python qa/run.py --test test_payment_and_ticket_journey
python -m playwright install firefox
python qa/run.py --browser firefox
```

## Coverage

1. Registration validation, account creation and authenticated navigation.
2. Search, budget filtering and empty states.
3. Favorite add/remove.
4. Sector visibility, price budget, eight-seat selection limit, summary totals.
5. Real payment decline → approval → QR rendering → calendar download.
6. Cancellation and seat release.
7. Countdown disablement, server expiry and payment controls removed.
8. Reservation idempotency and repeated payment without duplicate tickets.
9. Stale-seat conflict shown to the customer.
10. Live seat availability update and deselection of newly occupied seats.
11. Operations and booking ownership restrictions.
12. Gate-only role, check-in, duplicate prevention and denied financial access.
13. Event create/edit/delete and actual raster-poster upload.
14. Deletion blocked when booking history exists.
15. Audit log, payment attempts and CSV export.
16. Fourteen routes at 1440, 768 and 390 pixels; document-overflow checks and screenshots.
17. Keyboard-only seat selection.
18. Persistent RU/EN language switching and server-calculated promo discount.
19. Expanded header, support links, active navigation, mobile menu, Escape focus and reduced-motion behavior.
20. TICKETLY Control Django admin creation/inventory and responsive dashboard at three viewport widths.

The purchase flow follows detail → seats → contact/promo checkout → payment → success → ticket wallet. Public selectors match the supplied Figma integration.

Every test records page JavaScript errors and HTTP 5xx responses as failures. Fixtures are arranged through Django ORM in a separate thread so Playwright's event loop does not conflict with Django's sync ORM. Payment transport is never mocked.

## Artifacts and exit codes

- `report.html` and `report.json`: honest status and individual outcomes.
- Per-test `final.png`, responsive screenshots, video and `trace.zip`.
- `web.log`, `payment.log` and downloaded CSV/ICS fixtures.
- `.tmp/qa/latest.json` points to the most recent run.
- Exit **0**: executed tests passed; **1**: test failures; **2**: infrastructure blocked setup.

Inspect a trace:

```powershell
python -m playwright show-trace .tmp/qa/<run-id>/<test-name>/trace.zip
```

Artifacts contain synthetic accounts and test session tokens. They must not contain production data. The CI job uploads them for debugging.

## Limits

SQLite is suitable for serial browser journeys, not proof of concurrent PostgreSQL row locks. Run `python manage.py test booking payment_service` against PostgreSQL separately; CI config includes that check. A failed browser startup is **BLOCKED**, not a passing or silently skipped suite. CSS overflow tests and screenshots do not establish formal accessibility compliance or a subjective design ranking against competitors.
