# TICKETLY: PyCharm orqali ishga tushirish (UFARM-3845)

## Test natijasini to‘g‘ri o‘qish

Oxirgi lokal regressiya: `Ran 83 tests ... OK (skipped=1)`.
Bu **82 passed, 1 skipped, 0 failed** degani. SQLite parallel PostgreSQL
reservation testini bajarmaydi. `FAILED (...)` yoki undan keyingi traceback
bo‘lsa, buyruq muvaffaqiyatsiz hisoblanadi. Playwright browser ochilmagan
`WinError 5` holati alohida BLOCKED, vizual PASS emas.

## 1. Interpreter va paketlar

PyCharm’da `DEVOPS PROJECT` yoki klonlangan `DEVOPS-MID` papkasini **Open** qiling.
Settings → Project → Python Interpreter orqali Python 3.12 virtual environment
tanlang: Windows’da `.venv/Scripts/python.exe`, Linux’da `.venv/bin/python`.
Run konfiguratsiyalar project interpreter’dan foydalanadi, absolute user path yo‘q.

Windows PowerShell terminalida (loyiha ildizida):

```powershell
# Faqat .venv hali mavjud bo‘lmasa:
py -3.12 -m venv .venv

.\.venv\Scripts\python.exe -m ensurepip --upgrade
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
npm ci --ignore-scripts
npm run build
npm run check
```

Mavjud `.venv`ni o‘chirish shart emas. O‘rnatish xatosi chiqsa, keyingi bosqichga
o‘tmang. Python paketlari o‘rnatilganini tekshiring:

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -c "import django, whitenoise, redis; print(django.get_version())"
```

Bu sessiyada `.venv`da pip/Django topilmadi, ensurepip esa Windows vaqtinchalik
papkasiga yozishda ruxsat xatosi berdi. Shuning uchun IDE muhiti o‘rnatilgan deb
hisoblanmaydi; yuqoridagi buyruqlarni oddiy PyCharm terminalida tugating.

## 2. Run konfiguratsiyalari

Project ichidagi `.run/*.run.xml` fayllar PyCharm’ning Run menyusida ko‘rinadi.
Ko‘rinmasa projectni qayta oching yoki Run → Edit Configurations orqali tekshiring.
Python/Django pluginining maxsus server turi kerak emas: oddiy Python config ishlatilgan.

| Konfiguratsiya | Vazifa |
| --- | --- |
| Ticketly Migrate | Migrations + role groups; account yoki demo data yaratmaydi |
| Ticketly Payment | Payment simulator, `127.0.0.1:8001` |
| Ticketly Web | Django frontend/backend/admin, `127.0.0.1:8000` |
| Ticketly Expiry Worker | Muddati o‘tgan bronlarni bo‘shatadi |
| Ticketly Backend Tests | Booking/payment regressiya testlari |
| Ticketly Playwright | Izolyatsiyalangan browser AQA, 8990/8991 portlar |

Avval **Ticketly Migrate** tugasin. Keyin **Payment**, **Web** va **Expiry Worker**ni
alohida ishga tushiring. Har birini o‘z Run oynasidagi Stop tugmasi bilan to‘xtating.
`--noreload` debugger uchun qo‘yilgan: Python/template o‘zgarishidan keyin Web’ni restart qiling.

- Sayt: http://127.0.0.1:8000/
- Admin: http://127.0.0.1:8000/admin/
- Operations: http://127.0.0.1:8000/operations/
- Tayyorlik: http://127.0.0.1:8000/health/ready/

Konfiguratsiyalar DEBUG=1, SQLite va local cache bilan ishlaydi; DB_HOST/REDIS_URL
bo‘sh qiymatga o‘rnatilgan. Production `.env` ishlatilmaydi. Demo payment secret
web va payment uchun bir xil. Bu production deployment o‘rnini bosmaydi.

## 3. Admin va demo tadbirlar

Oddiy terminaldagi buyruqlarda IDE run environment avtomatik qo‘llanmaydi.
Quyidagi environment’ni shu terminalda o‘rnating:

```powershell
$env:DEBUG='1'
$env:DJANGO_SETTINGS_MODULE='config.settings'
$env:DB_HOST=''
$env:REDIS_URL=''
$env:SECRET_KEY='local-development-only-not-for-production'
$env:PAYMENT_SECRET='local-simulator-only'
$env:PAYMENT_URL='http://127.0.0.1:8001'
$env:SECURE_SSL_REDIRECT='0'
$env:TRUST_PROXY_HEADERS='0'
$env:ALLOWED_HOSTS='localhost,127.0.0.1,testserver'
$env:CSRF_TRUSTED_ORIGINS='http://localhost:8000,http://127.0.0.1:8000'
.\.venv\Scripts\python.exe manage.py createsuperuser
# Faqat sample tadbirlar kerak bo‘lsa:
.\.venv\Scripts\python.exe manage.py seed_demo
```

Parol terminalda interaktiv kiritiladi. `.env`, baza, `.idea` va credentiallar
Git’ga yuborilmaydi. `.run` ichida faqat lokal demo qiymatlar bor.

## 4. Test va Playwright

**Ticketly Backend Tests**ni ishga tushiring. Loyihada Django test runner ishlatiladi;
`pytest` o‘rnatish talab qilinmaydi. SQLite testlari lokal bazani almashtirmaydi.
PostgreSQL concurrency va container integration GitHub CI/Ubuntu Compose’da tekshiriladi.

Playwright uchun:

```powershell
.\.venv\Scripts\python.exe -m pip install -r qa/requirements.txt
.\.venv\Scripts\python.exe -m playwright install chromium
```

Keyin **Ticketly Playwright**ni Run qiling. U alohida SQLite bazasi va serverlarini
yaratadi; hisobot `.tmp/qa/<run>/report.html`, oxirgi natija `.tmp/qa/latest.json`da.
`WinError 5` browser boshlanishidan oldin chiqsa, bu environment blokidir. Oddiy
PyCharm terminalida sinang yoki Ubuntu’da `python qa/run.py` bajaring. Testni
skip qilish yoki Actions’dan olib tashlash bilan PASS deb belgilamang.

8000/8001 band bo‘lsa, avval o‘zingiz ishga tushirgan eski servisni to‘xtating.
Docker Compose 18000 portda ishlasa, lokal web 8000 bilan to‘qnashmaydi.

## 5. Push oldidan

```powershell
git status --short
git diff --check
git diff --stat
git add .run .github/workflows booking config templates qa/test_journeys.py deploy/README.md docs
git diff --cached --check
git diff --cached --stat
git commit -m "UFARM-3845: account security, PyCharm setup and CI/CD"
git push origin main
```

Main push release workflow orqali CI’ni ishga tushiradi. Testlar o‘tmaguncha image
publish/deploy bajarilmaydi. Production environment yoki SSH server sozlanmagan
bo‘lsa deploy hali tayyor emas; `deploy/README.md`ga qarang.
