# UFARM-3845: Ubuntu VM validation

The VM's successful `docker info` confirms engine access only. Run these steps
after pushing the latest fixes and checking the matching GitHub Actions commit.
Local Compose uses demo payments; this is not the production deployment.

## First checkout

```bash
git clone https://github.com/MuhammadAliQA/DEVOPS-MID.git
cd DEVOPS-MID
test -f .env || cp .env.example .env
chmod 600 .env
export WEB_PORT=18000
export CSRF_TRUSTED_ORIGINS=http://localhost:18000,http://127.0.0.1:18000
docker compose config --quiet
docker compose up --build -d
python3 scripts/compose_smoke.py
docker compose exec -T web python scripts/http_smoke.py --allow-demo-data
docker compose exec -T web python scripts/admin_smoke.py --allow-demo-data
docker compose exec -T web python scripts/container_assets_check.py
docker compose exec -T web python manage.py test booking payment_service --verbosity 2
```

Stop on a failed command and inspect `docker compose ps --all` and
`docker compose logs --tail=100`. Do not delete database volumes to fix failures.
Smoke tests create synthetic customer/event records. The Django test runner
creates a separate test database; it must finish successfully against PostgreSQL,
including the concurrency test skipped by local SQLite verification.

## Open the site

Inside the Ubuntu VM, open http://localhost:18000. Compose binds to loopback.
To view it from Windows, with SSH enabled on the VM, run:

```powershell
ssh -N -L 18000:127.0.0.1:18000 user@VM_IP
```

Then open http://localhost:18000 on Windows. Replace `VM_IP` with the VM's
reachable address. Keep the SSH terminal running.

Create your admin interactively (no password in command history):

```bash
docker compose exec web python manage.py createsuperuser
```

The catalogue is initially empty. Add real events through `/admin/`, or explicitly
load sample events for a demo with `docker compose exec web python manage.py seed_demo`.

## Update an existing checkout

```bash
git status --short
git pull --ff-only
export WEB_PORT=18000
export CSRF_TRUSTED_ORIGINS=http://localhost:18000,http://127.0.0.1:18000
docker compose up --build -d
python3 scripts/compose_smoke.py
```

Preserve local changes and `.env`. Repeat the smoke commands after each update.
Public HTTPS deployment, protected GitHub environment, immutable image release,
backup restore and rollback are documented separately in `deploy/README.md`.
