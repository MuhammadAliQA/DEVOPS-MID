# UFARM-3845: customer password change

The profile settings now link to `/accounts/password/change/`. Django's built-in
PasswordChangeView validates the current password, matching new passwords and the
configured password validators. CSRF and shared authentication rate limiting
apply. A successful change keeps the current browser session signed in and
invalidates other browser sessions on their next request. Existing JWT handling
is unchanged; this is not a token revocation feature or forgotten-password reset.

The form and confirmation page use the existing responsive design, explicit field
labels, password-manager autocomplete, validator hints and UZ/RU/EN customer copy.

Verification on 2026-11-17:

- Full backend/payment suite: 83 tests, 82 passed, one PostgreSQL concurrency test
  skipped because local verification uses SQLite.
- Four new tests cover validation, CSRF, anonymous access, session behavior,
  profile navigation and the three languages.
- Django check, migration drift, JavaScript syntax and whitespace checks passed.
- Local execution uses Django 5.0.6 with verification_settings excluding missing
  WhiteNoise; CI must validate the declared dependencies and PostgreSQL.
- Added a Playwright password-change/mobile scenario. Local browser startup was
  blocked by WinError 5 before execution; no browser pass is claimed.

Pending CI/CD changes also remain in this working tree. Main pushes trigger the
release workflow, which first runs CI. Deploy requires the production environment
and a reachable host as described in `deploy/README.md`.
