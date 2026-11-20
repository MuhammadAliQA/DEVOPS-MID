# 🎟️ TICKETLY

**Event Booking & Ticket Management Platform**

TICKETLY — konsert, teatr, sport, festival va konferensiyalar uchun chipta bron qilish platformasi. Foydalanuvchilar tadbirlarni topishi, sxemadan o‘rindiq tanlashi, 10 daqiqaga bron qilishi, demo to‘lovni amalga oshirishi va QR chipta olishi mumkin.

Loyiha DevOps Mid-Term o‘quv ishi sifatida ishlab chiqilgan. Unda dasturiy ta'minot bilan birga Docker, CI/CD, avtomatlashtirilgan testlar, deployment va monitoring jarayonlari ham qamrab olingan.

> ⚠️ **Educational Project:** To‘lovlar simulyatsiya qilinadi. Haqiqiy pul yechilmaydi va karta ma'lumotlari yig‘ilmaydi.

## ✨ Key Features

### Customer Features
- Tadbirlarni qidirish va filtrlash.
- Sxema orqali o‘rindiq tanlash va jonli bandlik holati.
- 10 daqiqalik vaqtinchalik bron va countdown.
- Promokod va demo payment.
- QR chiptalar va `.ics` kalendar integratsiyasi.
- Booking cancellation va refund.
- Favorites va foydalanuvchi profili.
- O‘zbek, rus va ingliz tillari.

### Staff & Administration
- QR orqali ticket scanning va check-in.
- Operatorlar paneli: daromad, sotilgan chiptalar va statistika.
- Event CRUD va poster upload.
- Booking va payment attempt boshqaruvi.
- Audit logging va CSV export.
- Role-based permissions.

### User Interface
- Responsive design.
- Anime.js asosidagi animatsiyalar.
- Keyboard accessibility.
- `prefers-reduced-motion` qo‘llab-quvvatlashi.

## 🧱 Technology Stack

| Layer | Technologies |
|---|---|
| Backend | Python 3.12, Django 5.2, Django REST Framework, SimpleJWT |
| Database | SQLite (development), PostgreSQL (production) |
| Cache & Rate Limiting | Redis, LocMem |
| Background Tasks | Celery, Celery Beat |
| Payment | Django Payment Simulator, HMAC-SHA256 |
| Frontend | Django Templates, JavaScript, CSS, Anime.js |
| Static Files | WhiteNoise |
| QR Generation | qrcode, Pillow |
| Infrastructure | Docker, Docker Compose, Gunicorn, Caddy |
| CI/CD | GitHub Actions |
| Testing | Django TestCase, Playwright |

## 🏗️ Architecture

```text
                  Browser
                     |
                     v
               Caddy (HTTPS)
                     |
                     v
             Django + Gunicorn
                /    |     \
               /     |      \
              v      v       v
        PostgreSQL  Redis  Payment Service
                            (Simulator)

                 Celery Worker
                       ^
                       |
                  Celery Beat
                       |
                       v
               Booking Expiration
                 & Seat Release
```

### Important Design Decisions

- `select_for_update` orqali booking va seat consistency himoyalanadi.
- `Idempotency-Key` takroriy booking so‘rovlarini nazorat qiladi.
- Payment service bilan so‘rovlar HMAC-SHA256 orqali imzolanadi.
- Authentication endpointlari uchun rate limiting mavjud.
- `X-Request-ID` orqali so‘rovlarni kuzatish mumkin.
- Booking, payment, refund va check-in amallari audit log'ga yoziladi.
- Celery muddati tugagan bronlarni avtomatik yakunlaydi va o‘rindiqlarni bo‘shatadi.

Batafsil: `docs/architecture.md`.

## 🚀 Installation

### Prerequisites

- Python 3.12+
- Git
- Docker va Docker Compose (containerized setup uchun)

### Local Development

```bash
git clone https://github.com/MuhammadAliQA/DEVOPS-MID.git
cd DEVOPS-MID

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

python manage.py migrate
python manage.py setup_roles
python manage.py seed_demo
python manage.py createsuperuser

python manage.py runserver
```

Application: `http://127.0.0.1:8000`

Demo payment service — alohida terminalda:

```bash
DJANGO_SETTINGS_MODULE=payment_service.settings \
python -m django runserver 8001
```

Demo promo code: `TICKETLY10` — 10% discount.

### Docker Deployment

```bash
docker compose up --build -d
```

Service status:

```bash
docker compose ps
```

Logs:

```bash
docker compose logs -f
```

## ⚙️ Environment Variables

Configure environment variables in `.env`.

| Variable | Description |
|---|---|
| `DEBUG` | Development / production mode |
| `SECRET_KEY` | Django secret key |
| `PAYMENT_SECRET` | Payment request signing secret |
| `PAYMENT_URL` | Payment simulator URL |
| `ALLOWED_HOSTS` | Allowed application hosts |
| `CSRF_TRUSTED_ORIGINS` | Trusted CSRF origins |
| `REFUND_WINDOW_HOURS` | Refund eligibility window |

Production configuration example: `deploy/.env.production.example`.

Never commit real secrets or production credentials.

## 🔌 API

Full API documentation: `docs/api.md`.

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/events/` | Event listing and filters |
| GET | `/api/events/{id}/` | Event details |
| GET | `/api/events/{id}/seats/` | Seat availability |
| GET / POST | `/api/bookings/` | List / create bookings |
| POST | `/api/bookings/{id}/pay/` | Payment |
| POST | `/api/bookings/{id}/refund/` | Refund |
| POST | `/api/bookings/{id}/cancel/` | Cancel booking |
| POST | `/api/token/` | JWT authentication |

### Health Checks

- `/health/live/`
- `/health/ready/`

## 🧪 Testing

### Backend Tests

```bash
docker compose exec web python manage.py test booking -v 2
```

### JavaScript Checks

```bash
npm run check
```

### Playwright Browser Tests

Install QA dependencies:

```bash
python3 -m venv .venv-qa
source .venv-qa/bin/activate

pip install -r qa/requirements.txt
playwright install chromium
```

Run browser tests:

```bash
.venv-qa/bin/python qa/run.py
```

Run a specific browser test:

```bash
.venv-qa/bin/python qa/run.py --test test_payment_and_ticket_journey
```

**Important:** Playwright tests must run through `qa/run.py`. Do not run them through Django's test runner or `unittest discover`.

### Latest Verified Results

| Test Suite | Result |
|---|---:|
| Backend booking tests | 108 passed |
| Playwright browser tests | 21 passed |
| Total successful tests | **129** |
| Failed tests | 0 |
| Skipped backend tests | 1 |

Playwright reports, screenshots and traces are saved in `.tmp/qa/`.

## 🔄 CI/CD & Deployment

- **GitHub Actions:** Automated checks and CI workflows.
- **Docker Compose:** Containerized application services.
- **Caddy:** Production reverse proxy and HTTPS.
- **Release automation:** `deploy/release.py`.
- **Production configuration:** `deploy/compose.production.yaml`.

Operational documentation:
- `docs/runbook.md`
- `docs/ubuntu-compose-start.md`

## 📁 Project Structure

```text
DEVOPS-MID/
├── booking/          # Booking, events, tickets and API
├── payment_service/  # Payment simulator
├── config/           # Django configuration and Celery
├── templates/        # HTML templates
├── static/           # CSS, JavaScript and assets
├── deploy/           # Docker, Caddy and release scripts
├── qa/               # Playwright browser tests
├── docs/              # Architecture, API and runbooks
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── manage.py
```
