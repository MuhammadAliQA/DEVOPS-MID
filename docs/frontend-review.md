> Current direction (17 November 2026): supplied Figma ZIP imported as `design-reference/`. Its dark/violet TICKETLY layout is now connected to Django. See [current verification](figma-verification.md). Older visual decisions below are historical; competitor access remains unverified.

# Frontend / competitor review — 16 November 2026

## Evidence and limits

Read `product-vision.md` and `competitor-analysis.md` in full. HTTP retrieval was attempted for https://iticket.uz, https://sxodim.uz, https://myticket.uz, https://ticketgo.uz and https://olbilet.uz. Every request failed with a connection-refused error in this execution environment. No competitor screenshots, live flows, authenticated dashboards, DOM measurements or network traces were available.

The original matrix is therefore **supplied research, not independently verified evidence**. Claims about market share, specific frameworks, SSR/ISR, performance rankings, universal absence of organizer/staff tools and app parity cannot be established from the supplied material alone. Private B2B portals may exist even if absent from public navigation.

The supplied documents also disagree in places:

- Vision says organizer portals are universally absent while the matrix lists Sxodim B2B presence and iTicket as unknown.
- Ticket gifting is described as Level 2 in lessons but Level 3 in the feature table.
- Guest checkout and AI recommendations appear as differentiation ideas without being MVP requirements.
- Next.js is prescribed based on an unverified competitor stack claim. The user explicitly requested Django; this implementation uses server-rendered Django instead.

## Product decisions derived from supplied research

| Source in supplied analysis | Design requirement | Implemented behavior |
|---|---|---|
| iTicket seat map depth | Visible price/state and reliable allocation | A/VIP sector switch, priced seats, disabled occupied seats, atomic reservation |
| Sxodim budget filtering and wishlist | Help users stay within budget and save plans | Seat-budget highlighting, favorites, catalog price cap |
| MyTicket poster-first catalog | Event identity before dense metadata | Original CSS graphic posters, date/venue/price hierarchy |
| TicketGo uncluttered checkout | Short purchase path and understandable status | One seat summary, clear amount, explicit simulated approval/decline |
| Olbilet discovery and booking timer | Discoverability and clear reservation deadline | Server-rendered search/filter results, ten-minute countdown |
| Cross-platform trust gaps | Explain price and policy before purchase | UZS totals, zero service fee, per-event refund-policy text |
| Operations gaps from product vision | Staff tools beyond generic admin | Custom dashboard, sales chart, inventory creator, booking table, CSV, check-in |

These are independent design choices, not reproductions of competitor pages. Logos, proprietary artwork and page layouts were not copied.

## Visual direction

- Dark navy canvas, slate panels, warm amber accent and quiet borders.
- Editorial hero using local CSS shapes and typography; six fictional demo events.
- Poster-first responsive grid with category-specific geometric artwork.
- Event page separates event context, seat map and price summary.
- Seat controls use native checkbox semantics; selected seats remain selected when switching sectors. Budget highlighting is advisory, not an enforced price limit.
- Operations uses a fixed desktop sidebar, compact navigation on mobile, restrained metric cards, seven-day bars, attendance ring and dense data tables with horizontal overflow.
- Charts show actual database totals, including honest zero/empty states. There are no fabricated growth percentages or pretend notifications.
- Inputs have accessible names, keyboard focus styling, server-side errors and reduced-motion support. Formal WCAG conformance is not claimed.

## Live audit still needed

When browser/network access is available, capture dated desktop/mobile evidence for each competitor: discovery → filters → seat selection → hold → checkout, plus refund policy and public B2B links. Separate public observations from authenticated/private features. Measure real keyboard/touch behavior, JS console errors and page performance. Do not turn a framework guess into a factual performance comparison.

For TicketFlow verify 1440px, 768px and 390px layouts, maximum event/title lengths, keyboard-only seat selection, expired checkout, no results, no tickets, declined payment, empty Operations and populated charts. Browser automation was attempted locally but blocked by Windows named-pipe permissions; no screenshot-based approval is claimed.
