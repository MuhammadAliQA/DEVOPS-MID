# TicketFlow API

Base path: `/api/`. JSON requests; amounts are positive integer UZS, not floats. JWT clients use `Authorization: Bearer <access>`. Browser sessions instead use CSRF-protected forms.

| Method | Path | Access | Payload / result |
|---|---|---|---|
| POST | `/api/register/` | Public | `username`, `password1`, `password2`; Django password validation |
| POST | `/api/token/` | Public | `username`, `password`; returns `access`, `refresh` |
| POST | `/api/token/refresh/` | Public | `refresh`; returns new `access` |
| GET | `/api/events/` | Public | Published upcoming events |
| GET | `/api/events/{id}/seats/` | Public | Seat IDs, sectors, row/number, prices, availability |
| POST | `/api/bookings/` | Authenticated | `{"event":1,"seats":[1,2]}`; 201 with UUID, total, expiry |
| GET | `/api/bookings/{uuid}/` | Owner | State, amount, expiry, ticket UUIDs |
| POST | `/api/bookings/{uuid}/pay/` | Owner | `{"outcome":"approve"}` or `decline`; paid state on success |

Malformed reservation input returns 400, unavailable seats return 409, another customer's resource returns 404. Anonymous access to protected endpoints returns 401 under JWT authentication. Public API requests use a basic 60/minute per-process DRF throttle; this is not a distributed abuse-prevention service.

## Internal payment simulator

`POST http://payment:8001/charge/` accepts JSON `booking` (UUID), `amount` (positive integer), `currency` (`UZS`), `outcome` (`approve` / `decline`). `X-Signature` is the lowercase hex HMAC-SHA256 of the raw request body using `PAYMENT_SECRET`.

Response: `{"status":"approved","reference":"<64-character hash>","simulated":true}`. An invalid signature gives 403; malformed data gives 400. Retries with the same booking and amount produce the same reference. It is internal-only in Compose and has no browser payment credentials.

## Reservation retry contract

Supply `Idempotency-Key: <UUID>` on POST `/api/bookings/`. The key is scoped to the authenticated customer. Replaying identical input returns the same booking (including current expired/cancelled/paid state), never a new reservation. Reusing a key for different input returns 409 with `code: idempotency_conflict`. Errors expose a stable `code` alongside the human-readable `detail`. Three active holds per customer and a recent payment-attempt guard prevent straightforward inventory/payment spamming; additional edge/distributed rate limiting is still needed for public deployment.
# Backend additions (17 November 2026)

Authenticated endpoints (session + CSRF or Bearer JWT), scoped to the current booking owner:

- `POST /api/bookings/{uuid}/checkout/`: `contact_name`, `contact_email`, optional `contact_phone` and `promo_code`. Returns `id`, `subtotal`, `discount`, `total`, `currency`, `status`. Invalid contact fields: 400; expired/frozen/invalid promo state: 409. Client-supplied amounts are ignored.
- `POST /api/bookings/{uuid}/cancel/`: releases a held booking and returns its cancelled status. Another user's booking returns 404; invalid state returns 409.

All web/API responses carry a generated `X-Request-ID`. Authentication POST endpoints share a configurable IP limit (default 20 per fixed minute). Exceeding it returns 429 with `Retry-After`; shared-cache failure returns 503. Production trusts only the IP header overwritten by the private Caddy ingress.

