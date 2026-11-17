# Single-host release runbook — UFARM-3845

Target: Linux VPS, Docker Engine + Compose v2, Python 3.12, public DNS and ports 80/443. The production file is standalone; do not merge it with local `compose.yaml`. The app, payment, PostgreSQL and Redis ports remain private. Caddy terminates HTTPS and overwrites trusted proxy headers. Do not expose `web:8000` directly or put an untrusted proxy in front of Caddy.

## One-time setup

1. Put this repository on the host (including `deploy/`). Copy `.env.production.example` to `.env.production` and set exact domain, TLS email, three independent secrets and a release image digest. Secret key: 64 random bytes; payment secret: at least 32 random bytes. Restrict the env file to the deployment account (`chmod 600`). Never upload it to GitHub.
2. Point DNS to the host. If GHCR is private, authenticate the host with a read-only packages token via `docker login --password-stdin`.
3. In GitHub, create a protected `production` environment with required reviewers. Configure `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_PATH` (absolute path without spaces), `APP_HOST` as environment variables; configure `DEPLOY_SSH_KEY` and `DEPLOY_KNOWN_HOSTS` as secrets. Populate known_hosts using a host key verified independently; the workflow does not blindly trust ssh-keyscan output.
4. Trigger the release workflow. Its reusable CI must pass before publishing. Deployment is opt-in and requires environment approval. No workflow has been executed remotely in this workspace.

## Release / rollback

```sh
python deploy/release.py --image ghcr.io/owner/repo@sha256:THE_DIGEST --verify-url https://tickets.example.com/health/ready/
python deploy/release.py --rollback --verify-url https://tickets.example.com/health/ready/
```

Release pulls an immutable image, starts DB/cache, stops web/expiry writes for a short maintenance window, backs up database and uploads, migrates, runs Django deployment checks, then waits for app/payment/worker health and checks public HTTPS. State is saved only on success. This is a single-host maintenance-window deployment, not zero downtime or high availability.

Rollback means **previous application image, current database schema**. Only use it after verifying backward-compatible migrations. Schema rollback and financial data deletion are never automatic. If a release fails, inspect `docker compose --env-file deploy/.env.production -f deploy/compose.production.yaml logs --tail=100`. A first release has no previous image. If schema upgrade succeeded, either fix forward or explicitly select a compatible previous image with `--image`; do not blindly reverse migrations. `.release.lock` prevents simultaneous runs; after a crashed process, verify no release is running before removing its stale lock.

## Backups and restore drills

Every release writes `deploy/backups/<UTC timestamp>/database.dump` and `uploads.tar.gz`; the directory is private and contains personal data. Replicate encrypted backups off-host and apply retention externally: keeping copies only on this VPS is not disaster recovery. The release performs an archive-read check, not a full restore.

```sh
python deploy/restore_drill.py deploy/backups/TIMESTAMP/database.dump --image ghcr.io/owner/repo@sha256:THE_DIGEST
```

The drill restores into a unique temporary DB on the same PostgreSQL instance, verifies paid booking/payment/ticket and seat state invariants, and drops only that temporary DB. It never overwrites the application DB. Run against a copy of production on a staging host when resources are constrained. Upload archives must also be restored to a staging volume and sampled separately. First-install dumps taken before migrations have no booking tables and cannot pass this application-level drill.

## Observability and failures

- `/health/live/`: process only. `/health/ready/`: DB + shared cache. No credentials/details returned.
- Expiry worker health requires a successful sweep in the last 60 seconds. Container restarts alone do not prove worker progress.
- JSON app logs contain generated request ID, route pattern, method, status and duration. Request bodies, card/contact data and query strings are not included by the app logger. Reverse-proxy/access logs still require appropriate retention and access controls.
- `X-Request-ID` connects user-visible failures to logs. Auth endpoints use shared Redis counters; Redis failure blocks authentication with 503 instead of silently disabling throttling.
- Watch readiness, worker unhealthy state, 5xx frequency and request latency. Centralized monitoring/alerts and off-host backup destinations require infrastructure configuration; none is claimed as deployed here.
- Real payment/refund integration remains out of the demo implementation. No live card collection or money movement is enabled.
