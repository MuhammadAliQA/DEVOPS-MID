# O‘zgarishlar (19-noyabr 2026)

## Topilgan va tuzatilgan buglar

| # | Muammo | Tuzatish |
|---|---|---|
| 1 | Kirish nazoratchisi (`/staff/scan/`) takroriy/yaroqsiz chiptada noto‘g‘ri xabar ko‘rardi: «Joy band, bron yopilgan…» | Aniq xato kodlari (`ticket_used`, `ticket_invalid`, `seat_unavailable`, `booking_closed`, `invalid_selection`) va tarjimalari |
| 2 | Mavjud bo‘lmagan chipta UUID `/operations/gate/` da 404 sahifa berardi | Do‘stona xabar |
| 3 | Maydonlar filtrida bir xil joy bir necha marta chiqardi (`DISTINCT` + `Meta.ordering`) | `order_by('venue')`, faqat kelgusi tadbirlar |
| 4 | Tadbir bo‘lmaganda bosh sahifada «—» qoldig‘i | Shablonda tekshiruv |
| 5 | Chiptasiz tadbirda «0 UZS» ko‘rinardi | «—» |
| 6 | Har bir sahifa ochilishi va 5 soniyalik o‘rindiq so‘rovi qator qulfi + yozuv bajarardi | `expire_event`: eskirgan bron yo‘q bo‘lsa — bitta SELECT, qulfsiz |
| 7 | Hamyon sahifasi barcha tadbirlarni qulflardi | `expire_user_holds` faqat muddati o‘tganlarni |
| 8 | Ro‘yxatdan o‘tishda `?next=` e’tiborga olinmasdi; bir email bir nechta hisobda ishlatilardi | `RegisterForm`, noyob email (ixtiyoriy maydon), profilda ham |
| 9 | Rasm xatosi tinglovchisi kech ulanib, ba’zi buzilgan rasmlar almashtirilmasdi | Ishga tushganda `complete && naturalWidth==0` tekshiruvi |
| 10 | O‘rindiq so‘rovi fon tabda ham, xatoda ham har 5 s takrorlanardi; band joyda `available` klassi qolardi | Fonda sekinlashadi, xatoda eksponensial kutish, klasslar sinxron |
| 11 | Taymer 0 dan keyin ham ishlardi | To‘xtaydi, `is-urgent` / `is-expired` holatlari |
| 12 | `pyproject.toml` da `redis` yo‘q edi | Qo‘shildi |
| 13 | Qidiruv maydonida ortiqcha `’`, «To’lov tekshirilmoqda’» | Tuzatildi |
| 14 | 404/403 sahifalari brend va tarjimasiz (TicketFlow), 500 sahifasi yo‘q | Uch tilli 404/403, mustaqil 500 |
| 15 | Joriy foydalanuvchilar uchun API cheklovi yo‘q edi | `UserRateThrottle` (600/min) |
| 16 | Statik fayllar siqilmasdi | WhiteNoise `CompressedStaticFilesStorage` |
| 17 | Ishlatilmaydigan `static/app.js` | O‘chirildi |
| 18 | Ops panelida qaytarilgan to‘lovlar daromadga qo‘shilardi | Qaytarilganlar hisobdan chiqarildi |

## Yangi backend imkoniyatlari

- **Pulni qaytarish (refund)**: `Booking.Status.REFUNDED`, migratsiya `0005`. Faqat to‘langan, qaytarishga ruxsat berilgan tadbir, boshlanishidan ≥ `REFUND_WINDOW_HOURS` (24) oldin va chipta skanerlanmagan bo‘lsa. O‘rindiqlar sotuvga qaytadi, chiptalar bekor bo‘ladi, audit yoziladi. Web: Chiptalarim → «Pulni qaytarish»; API: `POST /api/bookings/{id}/refund/`.
- **API**: `/api/events/` filtr, tartib, `limit/offset`, `X-Total-Count`, narx va bo‘sh joylar soni; `/api/events/{id}/`; `GET /api/bookings/`; barqaror xato kodlari. Eski javob formati (oddiy ro‘yxat) saqlangan.
- `favorite` — `X-Requested-With: fetch` bo‘lsa JSON qaytaradi (sahifa qayta yuklanmasdan yurak animatsiyasi).

## Animatsiyalar (Anime.js 4.5)

Hero: so‘zma-so‘z sarlavha, orbita nuqtasi aylanishi, parallaks, kursor yorug‘ligi, Ken Burns. Skroll: progress chizig‘i, yashiriluvchi/shishasimon sarlavha, kartalar va bo‘limlarning ketma-ket paydo bo‘lishi, rasmlar yuklangach silliq ochilishi. Kartalar: 3D tilt + yorug‘lik. O‘rindiqlar: markazdan to‘lqin, tanlashda bahor effekti va halqa, band bo‘lganda silkinish. Yurak: zarrachalar portlashi, kartani olib tashlash. Hisoblagichlar, progress/diagramma/halqa o‘sishi (operator paneli), jadval qatorlari. Muvaffaqiyat sahifasi: chizilgan belgi + konfetti. Toastlar (avto-yopilish), tasdiqlash dialogi (bekor qilish/qaytarish), taymer ogohlantirishi, tugma «ripple», sahifalar orasida View Transitions.

Xavfsizlik: `prefers-reduced-motion`, JS o‘chiq holat va 3 soniyalik CSS zaxirasi tekshirilgan; pul summalari animatsiya qilinmaydi.

## Testlar

Backend: 87 → 113 (yangi `booking/test_improvements.py`). Brauzer: 21/21 Playwright stsenariysi (ikkitasi yangilandi: yurak va bekor qilish dialogi). `QA_BROWSER_PATH`, `QA_NO_VIDEO` ixtiyoriy o‘zgaruvchilari qo‘shildi.

## Ma’lumot sifatida (o‘zgartirilmagan)

- `DEBUG` standart qiymati `1`; production uchun `.env` da `DEBUG=0` bo‘lishi shart (kod tekshiradi).
- CSP sarlavhasi yo‘q: sayt tashqi rasm (Unsplash) va inline uslublardan foydalanadi.
