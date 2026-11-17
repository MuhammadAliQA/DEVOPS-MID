# UFARM-3845 — Figma integration verification

Date: 17 November 2026.

## Layout and navigation follow-up

- Fixed the detail photo wrapper: the template used `detail-hero` while the exported stylesheet targets `detail-visual`. The missing positioning context made its absolute gradient and image geometry incorrect.
- Added `static/layout.css`: constrained grids, wrapping translated titles, aligned card prices, mobile vertical catalog, dedicated portrait cards and support sidebar. Header collapses at 1100px to fit the expanded navigation.
- Header now exposes Discover, Events, Artists, Venues and a keyboard-accessible Help disclosure (Help center, Terms, Privacy). Tickets and Profile remain header actions. Escape closes menus and restores focus.
- Added short entrance/hover/menu animations, disabled for reduced-motion preferences.
- Added separate `artist_photo` and `venue_photo` fields in Operations and migration 0004. Directories no longer reuse event posters. Missing portraits use initials; no unverified photo is presented as the actual artist. Real portraits await artist identities/source URLs from the user (current seed groups are labelled TICKETLY Demo).
- Follow-up verification: **9 Figma integration tests passed**, including three-language routes and photo-type separation; `.tmp/layout-tests.log`. The earlier full-suite results below predate this follow-up.
- AQA now has **19 scenarios**. The navigation/mobile/reduced-motion scenario was attempted but blocked before browser launch by the same WinError 5. Report: `.tmp/qa/20261117-095208-64aa/report.json`.

## Delivered

The user-supplied **Premium Event Ticketing Platform.zip** is preserved in `design-reference/`. Public Django pages use the export's component classes, full original stylesheet with integration overrides, dark/violet palette, photo hero, cards and checkout layouts. The reference's localStorage booking and decorative QR have been replaced with database-backed reservations and private scannable tickets.

- Home, filtered events, details, separate seats, contact/promo checkout, demo payment, success, ticket wallet and profile.
- Uzbek, Russian and English interface catalog; language cookie; optional localized event titles/descriptions editable in Operations.
- Artist/venue directories use actual published inventory. Help/privacy/terms links work.
- One real QR per purchased seat; QR download and calendar export.
- Server-calculated `TICKETLY10` discount; immutable pricing after any payment attempt. Contact validation, profile ownership and newsletter deduplication.
- Existing custom Operations, role permissions, event uploads, audit, payment attempts and check-in remain available.
- Figma sample external photo URLs are attached only to known seeded demo events without uploaded/reference images. User-created events and booking history are preserved.

## Actual checks

| Check | Result |
|---|---|
| Django tests (booking + payment service) | **57 discovered, 56 passed, 1 skipped**; `.tmp/final-backend-tests.log` |
| Public routes in UZ/RU/EN | Server rendering passed in automated integration tests |
| Contact/promo/payment ownership and expiry | Passed |
| Full HTTP journey against two running services | Passed: Operations event creation, registration, search, reservation, 10% discount, decline/retry, approval, private QR, wallet, ICS, check-in, duplicate prevention and CSV |
| Django system check | No issues |
| Migration drift | No changes detected; migration 0003 applied locally |
| Static collection | Passed |
| Docker Compose configuration | `docker compose config --quiet`: exit 0 |
| Playwright browser startup | **BLOCKED**: Windows `PermissionError: [WinError 5]` creating the driver pipe; no browser test or visual comparison pass claimed |
| Docker engine | **BLOCKED**: access denied to `dockerDesktopLinuxEngine` named pipe |
| Remote CI / CD | CI workflow authored and updated, not run remotely; production CD/deployment not configured |

The PostgreSQL concurrency test is skipped on local SQLite. Available local Django is 5.0.6; intended requirements use 5.2.x. Verification removes unavailable WhiteNoise middleware via `.tmp/verification_settings.py`; production middleware was not removed. These local results do not certify the container or production dependency set.

The separate `qa/` suite now contains 18 browser scenarios and 42 responsive route/viewport combinations, including language switching and discounted checkout. JSON/HTML reports are under `.tmp/qa/`; `latest.json` points at the latest attempt. Browser scenarios are implemented but remain unexecuted in this restricted environment.

## Visual and integration limits

The ZIP contains no event photographs or font binaries. Unsplash photos and Google Fonts retain the supplied external sources; uploads take precedence and failed non-QR images get a local fallback. Offline appearance therefore differs from the reference. Pixel-level match, mobile overflow and screenshots require a working browser runtime and remain unverified.

Payment and newsletter delivery are explicitly demo-only. No real card data is accepted. The demo payment service is separate from Django booking; event/seat/booking/ticket transactions remain in one application to preserve atomic allocation. This is not a claim that five independently deployed microservices or a production payment provider have been delivered.
