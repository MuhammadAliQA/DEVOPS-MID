> Evidence review (UFARM-3845, 2026-11-16): This is supplied research. Live retrieval of all five competitor sites was attempted but blocked by connection-refused errors. Feature, market-share, framework and performance claims below have NOT been independently verified. See frontend-review.md for contradictions, design decisions and the remaining audit.

# TicketFlow — Competitor Analysis
> Uzbekistan Event Ticketing Market · Research Date: November 2026

---

## Platforms Analyzed

| Platform | URL | Operated By |
|---|---|---|
| iTicket | https://iticket.uz | JV LLC «ITICKET INGURUZ» |
| Sxodim | https://sxodim.uz | Sxodim.uz (part of Davay Sxodim ecosystem) |
| MyTicket | https://myticket.uz | ООО «MYTICKET CO» / Art Uz Promotion |
| TicketGo | https://ticketgo.uz | TICKETGO MCHJ |
| Olbilet | https://olbilet.uz | LLC «OLBILET» |

---

## 1. Competitor Feature Matrix

| Feature | iTicket | Sxodim | MyTicket | TicketGo | Olbilet |
|---|:---:|:---:|:---:|:---:|:---:|
| **Homepage hero carousel** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Quick date filter bar** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Category navigation** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **City/region switcher** | ✅ | ✅ | ❌ | ✅ | ❌ |
| **Language switcher (UZ/RU/EN)** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Live search with autocomplete** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Price range filter** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Venue filter** | ✅ | ✅ | ✅ | ❌ | ❌ |
| **Multi-faceted filter panel** | ✅ | Partial | ❌ | ❌ | ❌ |
| **Sort by price / popularity** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Favorites / Wishlist** | ❌ | ✅ | ❌ | ❌ | ❌ |
| **Interactive SVG seat map** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **On-map price tier filter** | ❌ | ✅ | ❌ | ❌ | ❌ |
| **Seat hover tooltip** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Zoom + pan seat map** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Reservation countdown timer** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **General admission counter** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **QR e-ticket delivery** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **PDF ticket download** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **SMS ticket delivery** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Offline ticket access (cached QR)** | ❌ | ✅ | ❌ | ❌ | ❌ |
| **Phone OTP authentication** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Google/Social login** | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Guest checkout** | ❌ | ❌ | ✅ | ✅ | ❌ |
| **My Tickets dashboard** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Promo code field** | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Gift a ticket** | ❌ | ✅ | ❌ | ❌ | ❌ |
| **Self-service refund request** | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Refund policy on event page** | Partial | ❌ | ✅ | ✅ | ✅ |
| **Calendar view** | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Similar events recommendations** | ❌ | ✅ | ❌ | ❌ | ❌ |
| **Add to calendar (Google/Apple)** | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Organizer portal** | Unknown | ✅ (B2B page) | ❌ | ❌ | ❌ |
| **Cinema schedule (multi-showtime)** | ❌ | ✅ | ❌ | Partial | ✅ |
| **Native mobile apps** | ✅ | ✅ | ❌ | ✅ | ✅ |
| **Physical box office integration** | ✅ | ✅ | ✅ | ❌ | ❌ |
| **Uzcard / Humo payment** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Payme / Click / Uzum payment** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Visa / Mastercard** | ✅ | ✅ | ✅ | ✅ | ✅ |

---

## 2. Per-Platform Deep Analysis

### 2.1 iTicket.uz — Market Leader

**Observable Strengths:**
- Strongest brand recognition and market share in Uzbekistan
- Full trilingual support (UZ/RU/EN) with dynamic URL paths
- Best-in-class SVG seat map with zoom, pan, hover tooltips, and color-coded price tiers
- Covers the widest range of venues: Humo Arena, Bolshoi Opera, Pakhtakor Stadium, etc.
- Multi-channel: online + physical box offices (kassas) across Tashkent and Samarkand
- Reservation countdown timer (10–15 min) prevents double-booking
- Complete local + international payment coverage
- General admission counter for standing-room zones

**UX Improvement Opportunities:**
- No wishlist/favorites feature visible
- No social login (Google/Apple) — OTP only creates friction for new users
- Mobile seat map suffers from touch density on large venues (12,000+ Humo Arena seats)
- Inflexible refund policy with no self-service workflow
- No "similar events" or personalized recommendations
- No "add to calendar" on confirmation page
- Occasional seat map freezing under high-traffic load

**TicketFlow Differentiation vs. iTicket:**
- Superior self-service refund request flow
- Personalized recommendations engine
- Favorites / wishlist
- Add to calendar + digital wallet (Google Wallet / Apple Wallet)
- Better mobile seat selection UX (sector-first approach)
- Transparent refund eligibility indicator before checkout

---

### 2.2 Sxodim.uz — Most Feature-Rich UX

**Observable Strengths:**
- Most advanced product among competitors — recently overhauled to "Sxodim 2.0"
- **On-map price budget filter** — unique feature not seen on others
- **"Gift a ticket"** feature for social sharing
- Wishlist/favorites with heart icon on event cards
- Offline ticket caching (QR accessible without internet)
- Similar events / recommendations carousel on detail page
- International phone OTP support (not just +998)
- City switcher for Tashkent/Samarkand/Bukhara
- Typo-tolerant search with transliteration support
- Multi-day session selector for theater runs

**UX Improvement Opportunities:**
- Web vs. native app parity gap (mobile web feels secondary)
- Refund policy not clearly shown per-event before checkout
- Language completeness: Uzbek translations sometimes incomplete
- Filter state resets cause page scroll jumps on web

**TicketFlow Differentiation vs. Sxodim:**
- Cleaner, more modern web-first experience (not just an app companion)
- Full Uzbek-first language design
- Transparent refund eligibility per-event before seat selection
- Organizer portal with self-service event creation
- QR check-in system for event staff

---

### 2.3 MyTicket.uz — Niche Concert Specialist

**Observable Strengths:**
- Strong focus on major Tashkent concert venues (Humo Arena, Druzhba Narodov)
- Clean grid layout with high-quality poster artwork
- Trilingual interface
- Interactive hall schema with color-coded price tiers
- Cart-level countdown timer (10–15 min reservation)
- Clear refund and exchange policy in footer

**UX Improvement Opportunities:**
- No price-range filter or sorting on catalog page
- Filter reset mechanisms inconsistent
- No wishlist feature
- No recommendations or related events
- No guest checkout — requires account creation
- Mobile seat map UX on large stadiums remains challenging

**TicketFlow Differentiation vs. MyTicket:**
- Advanced filtering (price slider, sort, multi-venue)
- Favorites and personalized recommendations
- Guest checkout option
- Full admin analytics for organizers

---

### 2.4 TicketGo.uz — Modern Challenger

**Observable Strengths:**
- Clean, uncluttered modern UI with no intrusive ads
- Full trilingual parity (UZ/RU/EN) with clean URL routing
- Complete domestic payment integration
- Interactive SVG seat maps with tooltips and color-coded tiers
- Telegram support channel integration
- Instant QR delivery + SMS + email + profile sync
- Guest checkout available

**UX Improvement Opportunities:**
- No price slider filter
- No venue-specific filter dropdown
- No wishlist / favorites
- Empty search states lack recommendations
- Mobile seat map touch precision issues on complex halls
- No self-service refund workflow in My Tickets
- Limited dark mode support
- No "add to calendar" or wallet integration

**TicketFlow Differentiation vs. TicketGo:**
- Advanced faceted filtering (price, venue, genre combined)
- Wishlist and favorites
- Sector-first mobile seat selection (better touch UX)
- Self-service refund management in My Tickets
- Organizer portal and analytics

---

### 2.5 Olbilet.uz — Full Entertainment Hub

**Observable Strengths:**
- **Broadest content scope**: concerts + cinema (multi-chain) + theme parks + sports
- Built on Next.js (SSR + ISR) — fastest initial load among competitors
- Telegram Bot authentication option
- Promo code / discount voucher field at checkout
- Cinema-specific workflow: date → cinema → format → showtime → seat
- 15-minute reservation countdown
- Comprehensive QR delivery (SMS + email + profile)
- Family attractions integration (Sky Park, Dino Park)

**UX Improvement Opportunities:**
- Lacks faceted filter depth (no price slider, no genre multi-select)
- No sorting dropdown on listing pages
- Bilingual content inconsistency (Russian vs. Uzbek event descriptions)
- No self-service refund request (requires manual support contact)
- Mobile seat map performance on dense venues

**TicketFlow Differentiation vs. Olbilet:**
- Better faceted filtering and sorting
- Clear per-event refund policy indicator
- Self-service refund request workflow
- Organizer self-service portal
- Event staff QR check-in system

---

## 3. Market Gap Analysis — What None of Them Do Well

| Gap | Opportunity for TicketFlow |
|---|---|
| Self-service refund requests | Build a refund request + status tracking flow in My Tickets |
| Organizer self-service portal | Full organizer portal with event creation, analytics, sales export |
| Event staff QR check-in system | Staff interface for scanning tickets at venue gates |
| Personalized recommendations | Rule-based "recommended for you" based on category/history |
| "Add to Calendar" / Wallet | Google Calendar + Apple Calendar links on confirmation |
| Sector-first mobile seat selection | 2-step zoom: pick sector → see individual seats |
| Transparent refund eligibility | Show refund policy badge on event cards and detail page |
| Advanced combined filters | Price + venue + category + date all in one filter panel |
| Promo codes | Discount code entry at checkout (only Olbilet has this) |
| Audit trail for admins | Admin activity log for all platform actions |

---

## 4. Competitive Positioning Strategy for TicketFlow

> **TicketFlow's Position:**
> *"The most customer-transparent, organizer-empowering, and staff-enabling event ticketing platform in Uzbekistan."*

**Three Pillars of Differentiation:**

### Pillar 1 — Customer Trust & Transparency
- Show refund eligibility status clearly before purchase
- Self-service refund requests (not manual support emails)
- Transparent seat availability without race conditions
- Honest booking status with clear expiry countdown

### Pillar 2 — Organizer Empowerment
- Full self-service organizer portal
- Real-time sales analytics and revenue tracking
- Event creation wizard with seat inventory management
- CSV/Excel sales report export

### Pillar 3 — Operational Excellence
- Event staff QR check-in interface
- Duplicate scan detection
- Atomic check-in validation on backend
- Real-time attendance dashboard

---

## 5. Technology Observations

| Platform | Observed Tech |
|---|---|
| iTicket | Custom React-like SPA |
| Sxodim | React (v2.0 rewrite), native iOS/Android apps |
| MyTicket | Unknown SPA |
| TicketGo | React SPA, native iOS/Android apps |
| Olbilet | **Next.js with SSR/ISR** — fastest and most SEO-friendly |

**TicketFlow will use Next.js App Router** (same as Olbilet), which is the most modern architecture observed in the market, and extends it with a superior developer experience, type safety, and comprehensive backend integration.
