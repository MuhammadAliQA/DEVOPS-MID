# UFARM-3845 — backend, delivery and motion update

17 November 2026. This record supersedes earlier feature/count summaries; it distinguishes implemented delivery tooling from an executed production deployment.

## Implemented

- Reservation expiry is capped at event start. Payment checks publication/start state both before calling the simulator and after the response; closure during payment records an abandoned attempt instead of issuing tickets.
- Owner-only API checkout and cancellation; checkout uses the same validated contact form, server prices and frozen promo logic as the website.
- Shared-cache authentication burst protection across web login/register and JWT token/register/refresh. Redis is used in Compose; local development uses in-process cache. Redis failure returns 503 for authentication; limit responses return 429 plus Retry-After. The production proxy overwrites client-IP headers and app ports are not published.
- Generated request correlation IDs, JSON route/status/latency logs, DB/cache readiness and successful-sweep worker heartbeat. SIGTERM/SIGINT stop the worker without waiting for a full sleep interval.
- Local Compose adds Redis, bounded app logs and worker health. Production Compose adds Caddy HTTPS, private backend ports, non-root read-only app containers and writable upload/tmp volumes.
- CI now includes dependency audit, release safety tests and real Compose health/HTTP integration stages.
- A manual release workflow reuses CI, publishes an immutable GHCR digest with provenance/SBOM, and optionally deploys through a protected production environment with pinned SSH host trust.
- Release tooling uses a maintenance window, DB/upload backup, migration, deployment checks and health-gated release recording. Rollback switches application images without reversing database migrations. An isolated restore drill validates core booking/payment/ticket invariants in a temporary database.
- Native Web Animations provide sequential hero entrance, viewport-triggered card reveals, seat/summary feedback and success animation. Reduced-motion cancels/disables animation; hidden tabs stop active animation. Repeated availability polling no longer rebuilds an unchanged selection list.

## Executed checks

| Check | Actual result |
|---|---|
| Django booking + payment tests | **65 discovered, 64 passed, 1 PostgreSQL-only concurrency test skipped**; `.tmp/platform-tests.log` |
| Release safety unit tests | **4 passed**; Docker/subprocess operations mocked, not a real deployment |
| Real customer/staff HTTP journey | Passed against two local services after restart; `.tmp/platform-http.log` |
| Readiness, X-Request-ID, worker heartbeat | Passed against running local service |
| Local and production Compose parsing | Both `config --quiet` checks exited 0; synthetic secrets and image digest used for production validation |
| Django production checks | No warnings with production settings; unavailable WhiteNoise removed only in local verification settings |
| Migration drift | No changes detected |
| Python, JS and workflow syntax | Python compilation, `node --check` for both frontend scripts and YAML parsing passed |
| Docker Engine | BLOCKED: access denied to Docker Desktop Linux engine named pipe |
| Browser execution | Remains blocked by WinError 5 creating Playwright driver pipe; no visual or animation runtime pass claimed |
| Remote CI, GHCR publish, TLS issuance, deploy, real backup/restore | **Not executed** — no target server/domain/registry environment has been supplied/configured |

Local available Django is 5.0.6 with SQLite and in-process cache. Intended dependency set is Django 5.2.x and PostgreSQL/Redis in containers. Distributed Redis throttling and PostgreSQL lock behavior therefore still require the configured CI/container checks. Dependency audit is configured in CI but was not run locally over the unavailable network.

## Animation source limits

Requested references: https://animejs.com/ and https://motion.dev/. Retrieval of both documentation sites failed at the configured proxy (connection refused). No claim is made that their latest examples were inspected or their packages installed. The delivered animation code uses the browser Web Animations API and the same general stagger/sequence/in-view/spring-like interaction patterns, without a third-party CDN/runtime. It is not an Anime.js or Motion package integration.

## Remaining deployment inputs and acceptance

See [deployment runbook](../deploy/README.md). Required inputs: Linux host, domain/DNS, registry access, independently verified SSH host key, environment secrets and protected GitHub environment. Configure off-host encrypted backup retention and alert destinations. Production HSTS includes subdomains/preload: confirm all descendants of the selected app hostname support HTTPS before enabling it publicly; this does not submit the hostname to the browser preload list.

The repository delivery work is implemented and locally checked to the extent shown above. DevOps cannot be called production-accepted until CI is green, containers run, the restore drill succeeds, public HTTPS passes and rollback compatibility is reviewed on the actual target. No real PSP/payment provider or newsletter delivery has been enabled.
