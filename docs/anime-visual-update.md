# TICKETLY Anime.js visual update — UFARM-3845

17 November 2026. Supersedes the earlier note that no animation package was integrated.

## Actual package integration

The user installed Anime.js 4.5.0, Motion 14.14.0 and motion-v 2.12.0. The installed Anime.js README, animation/timeline/timer type declarations and spring implementation were read. Motion's installed license and Anime.js license are MIT; this implementation needs no paid features. Only Anime.js is shipped to the browser. The user's other installed dependencies remain intact and are not loaded into Django pages.

`npm run build` copies the exact lockfile-installed UMD distribution to `static/vendor/`, preserving its MIT license and writing a version/SHA-256 manifest. The browser loads it before `static/motion.js`. No CDN is involved. The Dockerfile has a Node build stage; CI installs with `npm ci`, builds the vendor asset and checks JS syntax. Django still renders the website; no React/Vue migration was introduced.

## UI changes

- Hero: semantic heading sequence using `createTimeline`, subtle decorative orbit and consistent CTA hierarchy.
- Discovery: in-view card/section reveals with `stagger`, stronger poster/card hierarchy, readable metadata and separated UZS price area.
- Navigation: staggered mobile/help links, decorative icon feedback without moving click targets.
- Booking: visible three-step indicator, consistent panels and input focus/error states, spring feedback for seat selection and selection-summary updates. Server amounts are not animated through intermediate values.
- Tickets/profile/support: consistent borders, text contrast and surfaces; spring confirmation and ticket entrance on success.
- New `polish.css` builds on the supplied Figma layout and the existing responsive corrections.

Effects are one-shot and use opacity/transforms. Active animations revert inline styles after completion to avoid overriding responsive/hover styles. Reduced-motion changes and hidden tabs stop active effects immediately. Browser navigation is never delayed by an exit animation. All content remains present when JavaScript or the vendor asset is unavailable.

## Verification

- `npm run build` and `npm run check`: passed. Self-hosted Anime.js bundle: 118,043 bytes before HTTP compression.
- Actual vendored Anime.js timeline completion/revert and spring APIs exercised in Node: passed. This is API validation, not browser rendering.
- Nine Django Figma integration tests passed, including UZ/RU/EN route rendering and booking/contact/payment flows.
- Live HTTP pages and static assets returned 200; vendor-before-controller script ordering verified.
- Playwright navigation/reduced-motion scenario now also checks the loaded Anime.js API. Execution remains **blocked** before browser launch: `.tmp/qa/20261117-102116-7c0f/report.json`.
- A direct Chrome headless screenshot attempt also failed with Windows access denied at Mojo/CreateFile. No screenshot, pixel-match or browser-animation pass is claimed.

Source references inspected locally: `node_modules/animejs/README.md`, `dist/modules/timeline/timeline.d.ts`, `dist/modules/timer/timer.d.ts`, `dist/modules/animation/animation.d.ts`, `dist/modules/easings/spring/index.d.ts`, and both package license files. Public documentation URLs are https://animejs.com/documentation and https://motion.dev/docs; the earlier network retrieval restriction remains, so the installed-version references were used.
