# TicketFlow · UFARM-3845

Toshkent uchun Django asosidagi event-ticketing MVP: katalog → sektor/o‘rindiq → 10 daqiqalik bron → demo to‘lov → QR chipta.

**Ikki mustaqil HTTP servis:** Django web/booking va Django payment simulator. Event, seat, booking va ticket inventar yaxlitligi uchun bitta PostgreSQL tranzaksiya chegarasida turadi. Expiry worker alohida process/container. Bu beshta mustaqil domen mikroservisi emas; qaror [arxitekturada](docs/architecture.md) izohlangan.

## Ishga tushirish — Docker

Docker Desktop Linux engine ishlayotgan bo‘lishi kerak.

```powershell
Copy-Item .env.example .env
docker compose up --build -d
docker compose exec web python manage.py seed_demo
docker compose exec web python manage.py setup_roles
docker compose exec web python manage.py createsuperuser
```

- Sayt: http://localhost:8000/
- Maxsus Operations panel: http://localhost:8000/operations/
- Texnik Django admin: http://localhost:8000/admin/
- `createsuperuser` orqali yaratilgan hisob ikkala panelga kira oladi. Standart/paroli ochiq admin hisobi yo‘q.
- Demo tadbirlar xayoliy; `seed_demo` qayta ishga tushirilganda dublikat yaratmaydi.
- DB va payment portlari hostga chiqarilmaydi. Web faqat localhost orqali ochiladi.

## Docker bo‘lmasa — lokal development

Python 3.12, internetga ega pip va uchta terminal kerak. SQLite faqat bitta foydalanuvchili demo uchun; parallel bron kafolati PostgreSQL talab qiladi.

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python manage.py migrate
.venv\Scripts\python manage.py seed_demo
.venv\Scripts\python manage.py createsuperuser
.venv\Scripts\python manage.py runserver 127.0.0.1:8000
```

Ikkinchi terminal:

```powershell
.venv\Scripts\python manage.py runserver 127.0.0.1:8001 --settings=payment_service.settings
```

Uchinchi terminal:

```powershell
.venv\Scripts\python manage.py expire_bookings --loop
```

Lokal Django `.env` ni avtomatik o‘qimaydi; kerakli o‘zgaruvchilarni shell orqali o‘rnating. Compose esa `.env` ni o‘qiydi. Standart lokal konfiguratsiya yuqoridagi buyruqlar bilan ishlaydi.

## Tayyor imkoniyatlar

- Figma ZIP asosidagi TICKETLY: qora/violet uslub, foto hero, tadbir kartalari, alohida seat/checkout/payment sahifalari; UZ/RU/EN interfeys.
- Qidirish, kategoriya/joy/sana/narx filtrlari, narx bo‘yicha saralash, sevimlilar.
- A/VIP sektor tanlash, budjet belgisi, 8 tagacha o‘rindiq, server narxlari, 10 daqiqalik countdown.
- Idempotency-Key orqali xavfsiz bron qayta yuborish; bir mijozga 3 ta faol bron limiti.
- Payment success/decline/retry, saqlanadigan payment attempts, audit jurnali, cancellation va expiry.
- JPEG/PNG/WebP afisha yuklash (5 MB / 20 MP limit); afishalar DEBUG=False rejimida ham alohida endpoint orqali ochiladi.
- Event managers, Booking operators, Gate staff va Auditors rollari; staff flag yolg?iz o?zi ruxsat bermaydi.
- My Tickets, har bir joy uchun alohida QR, `.ics` kalendar yuklash.
- Session authentication + CSRF web uchun; JWT API uchun.
- **Custom Operations:** real DB KPI, 7 kunlik demo tushum grafigi, kirish ulushi, tadbir yaratish/tahrirlash, avtomatik seat inventory, bron filtrlari, faol bronni bekor qilish, CSV eksport, staff check-in.
- Docker Compose, non-root container, healthchecks, migratsiya jobi, expiry worker va PostgreSQL CI testlari.

QR kodi check-in havolasini saqlaydi. Xodim tizimga kirib, **POST bilan** kirishni tasdiqlaydi; havolani shunchaki ochish chiptani sarflamaydi. Kamera skaner ilovasi havolani ochishi yoki USB skaner uni Operations formaga kiritishi mumkin. Brauzer ichida kamera scanner SDK yo‘q.

## Tekshirish

QR renderer odatda `qrcode` kutubxonasini ishlatadi. U bo‘lmasa va OpenCV o‘rnatilgan bo‘lsa, haqiqiy QR yaratadigan qo‘shimcha backend ishlaydi; tanlovni `QR_BACKEND=qrcode` yoki `QR_BACKEND=opencv` bilan qat’iy belgilash mumkin. OpenCV ixtiyoriy (`opencv-python-headless>=4.10,<5`), container uchun kerak emas. Chiqadigan kod qayta dekodlash testi bilan tekshiriladi.

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test booking payment_service --verbosity 2
docker compose exec web python manage.py test booking payment_service --verbosity 2
```

Ikkala lokal servis ishlab turgan **demo bazada** to‘liq HTTP ssenariy:

```powershell
python scripts/http_smoke.py --allow-demo-data
```

Bu test haqiqiy CSRF/session formalar orqali yangi test hisoblari, tadbir va demo chipta yaratadi; ro‘yxatdan o‘tish, bron, declined/approved to‘lov, QR, kalendar, check-in va eksportni tekshiradi. Uni production bazada ishlatmang.

CI PostgreSQL bilan seat-lock concurrency testini va haqiqiy lokal HTTP payment smoke testini bajarishga sozlangan. Lokal muhitda olingan natijalar va cheklovlar: [verification.md](docs/verification.md).

## Playwright AQA

Alohida `qa/` papkasida 18 ta real brauzer ssenariysi bor. Ular test bazasi va ikki servisni o?zi yaratadi. Ishga tushirish: `python qa/run.py`. O?rnatish, coverage va trace hisobotlari: [qa/README.md](qa/README.md).

## Hujjatlar

- [Arxitektura va consistency](docs/architecture.md)
- [Frontend va competitor review](docs/frontend-review.md)
- [API](docs/api.md)
- [DevOps runbook](docs/runbook.md)
- [Dastlabki product vision](docs/product-vision.md)
- [Dastlabki competitor analysis](docs/competitor-analysis.md)

Real payment/refund, organizer tenancy, offline wallet/PWA va production deployment ushbu implementatsiyada yo‘q. Bu funksiyalarni UI soxta tayyor holatda ko‘rsatmaydi.

## Figma export integratsiyasi — 17 November 2026

Manba: foydalanuvchi bergan `Premium Event Ticketing Platform.zip`, o‘zgartirilmagan nusxasi `design-reference/`. Public UI `static/figma.css`, `static/figma.js` va Django templatelarida. Rasmlar eksportdagi tashqi Unsplash URLlardan, shriftlar Google Fontsdan yuklanadi; internet bo‘lmasa fallback ishlaydi. Operations alohida boshqaruv interfeysi sifatida saqlangan.

Bron → aloqa ma’lumotlari/promokod → demo to‘lov → tasdiq → har bir o‘rindiq uchun QR chipta. `TICKETLY10` kodi serverda 10% chegirma beradi; to‘lov urinishi boshlanganidan keyin chegirma o‘zgarmaydi. Profil, artistlar, maydonlar va email obuna ro‘yxati DB bilan ishlaydi; xabarnoma jo‘natish demo rejimida.

So‘nggi haqiqiy tekshiruvlar va qolgan muhit cheklovlari: [Figma verification](docs/figma-verification.md).
> Latest UFARM-3845 update: [backend/DevOps/motion verification](docs/platform-verification.md). Production release configuration and operating instructions: [deploy/README.md](deploy/README.md). Publishing/deployment workflows are implemented but have not been executed remotely.

> Anime.js is now integrated: run `npm ci` then `npm run build` before Django `collectstatic`. See [visual update and verification](docs/anime-visual-update.md). The browser uses the locally hosted Anime.js package; no paid animation feature is required.

> Admin revision: `/admin/` now uses TICKETLY Control and `/operations/` shares its branding. See [admin/Docker verification](docs/admin-docker-verification.md) for actual test results and the unresolved Docker engine access restriction.

