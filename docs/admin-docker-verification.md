# Admin and Docker revision — UFARM-3845

17 November 2026.

## Admin delivered

- `/admin/` now uses **TICKETLY Control**, built with Django's supported template/AdminSite overrides. No Jazzmin/Unfold dependency was installed or claimed. The existing Django authentication, permissions, CSRF, sidebar, theme toggle and form machinery remain in use.
- Permission-scoped dashboard cards; grouped event form, poster preview, RU/EN fields, explicit artist/venue images, search, filters and date navigation.
- Adding an event creates validated A/VIP inventory. Existing seat rows are read-only, including for superusers: forged seat-price/reservation fields cannot bypass booking consistency. The inventory section is collapsible.
- Event edits/deletion acquire the event lock used by booking services. Events with any booking history cannot be deleted; unsafe bulk delete is disabled. Admin writes create domain audit entries.
- Payment, booking, ticket, attempt and audit data are read-only. Newsletter subscriptions have a searchable read-only list. Cancellation/check-in stay in the purpose-built Operations flows.
- `/operations/` received matching violet/dark branding, responsive styling and permission-aware action links. Admin login is included in shared authentication throttling.
- Fixed a real form bug found by tests: Django admin's default split date field conflicted with the site's single datetime-local widget and prevented event saves.

## Docker changes

- Compose web port is configurable using `WEB_PORT` (default 8000).
- CI uses port 18000 for Compose, fixing a collision with its earlier Gunicorn service on port 8000.
- Migration service runs `bootstrap_platform`: schema plus least-privilege groups, without creating default passwords, users or demo events. Production migration service uses the same command.
- CI includes real HTTP admin CRUD and checks that Django/admin/custom CSS and Anime.js are served by the web container.

## Executed verification

| Check | Result |
|---|---|
| New admin tests | 9 passed: routing, creation/inventory/audit, invalid input, forged seat POST, financial read-only, history protection, role isolation, non-staff restriction and admin login limiting |
| Full booking/payment regression | **74 tests discovered, 73 passed, 1 PostgreSQL-only concurrency test skipped**; `.tmp/admin-regression.log` |
| Real HTTP admin | Login, dashboard, create, edit, search and delete passed with CSRF/session; `scripts/admin_smoke.py --allow-demo-data` |
| Operations/customer HTTP | Entire purchase, QR, check-in and CSV journey passed again; `.tmp/admin-operations-http.log` |
| Admin/static HTTP assets | Local server returned actual CSS/JS and 200 health/login responses; not a container-runtime result |
| Local + production Compose config | Both passed `config --quiet` |
| Production settings check | Passed with local verification middleware substitution and synthetic secrets |
| Docker startup | **BLOCKED**: attempted `WEB_PORT=18000 docker compose up --build -d`, Docker Desktop Linux engine named-pipe access denied |
| Browser admin/responsive scenario | **BLOCKED before execution**, WinError 5; `.tmp/qa/20261117-104020-48e2/report.json` |

The standalone AQA suite now has 20 browser scenarios. No screenshot, visual acceptance, successful container build/start, remote CI run or production deployment is claimed. Local checks use available Django 5.0.6/SQLite; CI targets requirements' Django 5.2.x/PostgreSQL.

## Re-run with a working Docker engine

```powershell
$env:WEB_PORT='18000'
docker compose up --build -d
python scripts/compose_smoke.py
docker compose exec -T web python scripts/admin_smoke.py --allow-demo-data
docker compose exec -T web python scripts/container_assets_check.py
```

These commands create synthetic demo records for verification. The admin smoke script disables its synthetic superuser in a `finally` block and removes its own unbooked event. Run on demo/staging, not a live ticket-sales database. Use existing admin credentials or create your own with `docker compose exec web python manage.py createsuperuser`; no default account/password is provisioned.
