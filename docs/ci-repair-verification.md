# UFARM-3845 verification: 2026-11-17

The initial local run reproduced five errors caused by Event fixtures missing
`starts_at`, plus an authentication rate-limit assertion failure. The working
tree already contained uncommitted changes to `booking/test_hardening.py`.

Changes preserve the new route tests while using valid inventory fixtures,
checking exact HTTP outcomes, and checking PNG/SVG validation through EventForm.
Streaming upload tests use TransactionTestCase so response-close signals do not
invalidate TestCase's enclosing PostgreSQL transaction. Removed manual connection
close/reopen logic. Original booking reliability and role-boundary tests are
retained in `booking/test_booking_reliability.py`. Rate-limit tests fix their clock
to avoid crossing a wall-clock bucket boundary during password hashing.

Verified locally:

- 79 Django/payment tests: 78 passed; PostgreSQL concurrency test skipped on SQLite.
- Four release safety unit tests passed (Docker mocked).
- Django system check and migration drift check passed.
- Frontend vendor build and JavaScript syntax checks passed.
- Local Compose configuration validation and Git whitespace check passed.

Local Python uses Django 5.0.6 and verification_settings omitting unavailable
WhiteNoise. This does not replace CI's required Django 5.2/PostgreSQL/container
and browser execution. Test output: `.tmp/final-ci-regression.log` (not committed).

Not verified in this session: GitHub Actions status (network connection failed),
Windows Docker runtime (engine access denied), browser AQA, remote deployment,
restore or rollback against real services. Git staging failed with
`.git/index.lock: Permission denied`; these fixes have not been committed or pushed.
The user's Ubuntu `docker info` shows a working engine on that separate VM.
Follow `docs/ubuntu-compose-start.md` there after pushing the fixes.
