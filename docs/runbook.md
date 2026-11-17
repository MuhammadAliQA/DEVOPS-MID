# Platform engineer runbook

> Updated delivery tooling: [production release/rollback and restore drill](../deploy/README.md). Current executed checks and remaining deployment inputs: [platform verification](platform-verification.md). The older local startup guidance below remains applicable; production now has authored tooling but has not been deployed.

## Startup and smoke checks

1. Copy `.env.example` to `.env` for local Compose. Start Docker Desktop's Linux engine.
2. `docker compose up --build -d` — the one-shot migration service must succeed.
3. `docker compose ps -a` and `docker compose logs --tail=100 web payment expiry-worker migrate`.
4. `docker compose exec web python manage.py seed_demo` and `createsuperuser`.
5. Check `/health/live/`, `/health/ready/`, `/`, `/operations/` (staff login).
6. Register a customer, select a seat, test declined then approved demo payment, inspect wallet QR, scan as staff and try a duplicate scan.

## Health, logs, and operational checks

- `/health/live/`: web process is responding; `/health/ready/`: DB accepts a query.
- Payment has `/health/live/` on its private port 8001.
- Gunicorn access/error logs go to stdout/stderr. Expiry worker logs processed event counts.
- Operations counts active holds by timestamp so elapsed holds are excluded even before the worker sweep.
- Watch 5xx rates, checkout latency, DB lock waits, stale `held` bookings, payment connection errors, and worker restarts. There is no deployed metrics/alerting stack in this repository.
- `docker compose exec web python manage.py expire_bookings` performs a one-off sweep. Run the loop worker continuously for prompt physical release.

## Failure handling

| Symptom | Inspect | Recovery |
|---|---|---|
| Checkout says payment unavailable | Payment health/logs and matching PAYMENT_SECRET | Restore simulator; retry before expiry. Do not manually mark bookings paid. |
| DB unavailable | DB health, storage, credentials | Restore DB; web readiness stays 503. |
| Holds look stale | Worker logs, server clocks, expires_at | Restore worker and run one sweep. Reservation/payment paths still enforce expiry. |
| Migration service exits nonzero | `docker compose logs migrate` | Correct migration/configuration before starting new web version. |
| Seat contention | PostgreSQL lock waits, event request volume | Reduce request rate; inspect transaction duration. Never disable locks. |
| QR already used | Ticket checked_in_at and gate staff workflow | Do not clear timestamp to admit a second visitor. Investigate manually. |

## Backup / restore

The named `postgres_data` volume persists data. `docker compose down` keeps it; `down -v` destroys it and must not be used for ordinary restart.

Create a custom-format backup *inside the DB container*, then copy it out to avoid Windows binary-redirection corruption:

```powershell
docker compose exec db pg_dump -U ticketflow -d ticketflow -Fc -f /tmp/ticketflow.dump
docker compose cp db:/tmp/ticketflow.dump ./ticketflow.dump
```

Store backups outside the repository with appropriate access controls. Practice restoring to an isolated PostgreSQL database with `pg_restore`; verify event/booking/payment/ticket counts and seat invariants before treating a backup as usable. Backup rotation and restore automation are not provisioned here.

## Production promotion is a separate deployment step

This repository is a local/university MVP, not a production-ready payment platform. Before public deployment:

- Pin/audit resolved dependencies and image digests; run CI and real PostgreSQL concurrency/load tests.
- Supply strong secret values through a secret manager, set DEBUG=0, configure exact hosts/origins and HTTPS termination. Secure cookies are enabled when DEBUG=0.
- TLS and reverse-proxy trust must be configured to match the actual ingress. SECURE_SSL_REDIRECT is opt-in; blindly enabling it behind an unconfigured proxy causes redirect loops.
- Add centralized logs, metrics/alerts, distributed throttling, DB backups and restore drills.
- Use least-privilege DB/application users, organizer-level permissions and audited operator changes if introducing multiple organizations.
- Run migrations as an explicit release job. Keep the previous image available for application rollback. Review backward compatibility before any schema rollback; never automatically reverse financial migrations.
- Real payments require verified PSP webhooks, a durable ledger and compensation/reconciliation design described in architecture.md.

No cloud resources, DNS, public deployment, registry publication or external Jira transitions were performed.
