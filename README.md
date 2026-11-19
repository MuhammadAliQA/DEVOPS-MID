# TICKETLY (DEVOPS-MID)

Django chipta bron qilish platformasi: tadbirlar, o‘rindiq tanlash, 10 daqiqalik bron, demo to‘lov (alohida `payment_service`), QR chiptalar, kirish nazorati va operatorlar paneli. Docker Compose, CI va production deploy skriptlari bilan birga.

## Tez ishga tushirish

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate && python manage.py setup_roles && python manage.py seed_demo
python manage.py runserver                       # sayt: http://127.0.0.1:8000
DJANGO_SETTINGS_MODULE=payment_service.settings python -m django runserver 8001   # demo to‘lov servisi
```

Docker: `docker compose up --build` (sayt `:8000`). Production: `deploy/` papkasi va `docs/runbook.md`.

## Tekshiruvlar

| Buyruq | Nima tekshiradi |
|---|---|
| `python manage.py test booking payment_service deploy` | Backend/unit/integratsiya testlari |
| `npm run check` | `motion.js` va `figma.js` sintaksisi |
| `python qa/run.py` | Haqiqiy brauzerdagi Playwright stsenariylari (`QA_BROWSER_PATH`, `QA_NO_VIDEO=1` ixtiyoriy) |

## Animatsiyalar

Anime.js 4.5 (`static/vendor`, build: `npm run build`) + `static/motion.js` / `static/motion.css`. Hammasi progressive enhancement: JS bo‘lmasa yoki `prefers-reduced-motion` yoqilgan bo‘lsa kontent darhol ko‘rinadi. Pul summalari hech qachon animatsiya qilinmaydi. Batafsil: `CHANGES.md`.

## API

`docs/api.md`. Asosiy: `/api/events/`, `/api/bookings/`, `/api/bookings/{id}/pay|refund|cancel/`, JWT: `/api/token/`.
