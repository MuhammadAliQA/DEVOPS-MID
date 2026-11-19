/* Anime.js 4.5: progressive enhancement, no scroll hijacking or delayed navigation.
   Local API references: animation/animation.d.ts, timeline/timeline.d.ts,
   easings/spring/index.d.ts and utils/stagger.d.ts in the installed package. */
(() => {
  const api = window.anime;
  if (!api?.animate || !api?.createTimeline) return;
  const {animate, createTimeline, spring, stagger} = api;
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const finePointer = matchMedia('(hover: hover) and (pointer: fine)');
  const active = new Set();
  const byElement = new WeakMap();
  const allowed = () => !reduced.matches && !document.hidden;
  const stop = () => {
    [...active].forEach(animation => animation.revert());
    active.clear();
    document.querySelectorAll('.is-animating').forEach(element => element.classList.remove('is-animating'));
  };
  const play = (targets, options = {}) => {
    if (!targets) return;
    const elements = typeof targets === 'string' ? [...document.querySelectorAll(targets)] : targets instanceof Element ? [targets] : [...targets];
    if (!allowed() || !elements.length) return;
    elements.forEach(element => {
      const previous = byElement.get(element);
      if (previous) {
        previous.revert(); active.delete(previous);
        previous.targets?.forEach(target => target.classList?.remove('is-animating'));
      }
    });
    elements.forEach(element => element.classList.add('is-animating'));
    const animation = animate(elements, {
      duration: 520, ease: 'outQuart', ...options,
      onComplete: self => {
        // Remove inline animation styles so hover/focus and responsive CSS stay in control.
        self.revert(); active.delete(self);
        elements.forEach(element => {
          if (byElement.get(element) === self) { byElement.delete(element); element.classList.remove('is-animating'); }
        });
      },
    });
    active.add(animation);
    elements.forEach(element => byElement.set(element, animation));
    return animation;
  };
  document.documentElement.classList.add('anime-motion');
  document.documentElement.dataset.motionEngine = 'animejs';

  // ── Page transition fade ─────────────────────────────────────────────────
  // Fade body out on internal link click, then let the browser navigate naturally.
  if (allowed()) {
    document.addEventListener('click', event => {
      const anchor = event.target.closest('a[href]');
      if (!anchor) return;
      const href = anchor.getAttribute('href');
      // Skip external links, same-page anchors, download links, and special targets.
      if (!href || href.startsWith('#') || href.startsWith('mailto:') || href.startsWith('tel:') ||
          anchor.origin !== location.origin || anchor.target || anchor.hasAttribute('download')) return;
      // Skip if modifier key held (new tab / open in background).
      if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      const dest = anchor.href;
      document.body.classList.add('page-exit');
      setTimeout(() => { location.href = dest; }, 220);
    });
    // Fade body back in on page load / bfcache restore.
    document.body.classList.add('page-enter');
    requestAnimationFrame(() => requestAnimationFrame(() => document.body.classList.remove('page-enter')));
    window.addEventListener('pageshow', event => {
      if (event.persisted) {
        document.body.classList.remove('page-exit');
        document.body.classList.add('page-enter');
        requestAnimationFrame(() => requestAnimationFrame(() => document.body.classList.remove('page-enter')));
      }
    });
  }

  // A short editorial hero sequence. Text stays semantic and selectable.
  if (allowed() && document.querySelector('.hero')) {
    const timeline = createTimeline({autoplay: false, defaults: {duration: 760, ease: 'outQuint'}, onComplete: self => {self.revert(); active.delete(self);}});
    const entries = ['.hero-meta', '.hero h1', '.hero-content > p', '.hero-info', '.hero-actions'];
    entries.forEach((selector, index) => {
      const element = document.querySelector(selector);
      if (element) timeline.add(element, {opacity: [0, 1], y: [24, 0]}, index * 85);
    });
    const ornament = document.querySelector('.hero-orbit');
    if (ornament) timeline.add(ornament, {opacity: [0, 1], scale: [.92, 1], rotate: [-8, 0], duration: 1300}, 100);
    active.add(timeline); timeline.play();
  } else {
    play('.page-heading, .flow-header', {opacity: [0, 1], y: [16, 0]});
  }

  // ── Scroll-reveal ────────────────────────────────────────────────────────
  // Reveal only when content enters the viewport; no hidden-content prerequisite.
  let observer;
  if ('IntersectionObserver' in window) {
    observer = new IntersectionObserver(entries => {
      const visible = entries.filter(entry => entry.isIntersecting);
      play(visible.map(entry => entry.target), {opacity: [0, 1], y: [20, 0], delay: stagger(55, {start: 0}), duration: 620});
      visible.forEach(entry => observer.unobserve(entry.target));
    }, {threshold: .07});
    // Extended set: original elements + wallet-card, profile-stats, flow-steps li, seat, ticket-tiers > div
    document.querySelectorAll(
      '.section-title, .event-card, .directory-card, .venue-card, .form-card, .order-card, ' +
      '.digital-ticket, .support-layout, .profile-hero, ' +
      '.wallet-card, .profile-stats, .flow-steps li, .seat, .ticket-tiers > div'
    ).forEach(element => observer.observe(element));
  }

  // ── Button ripple effect ─────────────────────────────────────────────────
  document.addEventListener('pointerdown', event => {
    const button = event.target.closest('.primary');
    if (!button || !allowed()) return;
    // Create ripple element positioned at click coordinates relative to button.
    const rect = button.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    const ripple = document.createElement('span');
    ripple.className = 'btn-ripple';
    ripple.style.cssText = `left:${x}px;top:${y}px`;
    button.appendChild(ripple);
    // Animate with CSS (keyframe defined in polish.css); remove after animation.
    ripple.addEventListener('animationend', () => ripple.remove(), {once: true});
  });

  // ── Skeleton shimmer ─────────────────────────────────────────────────────
  // Elements with [data-skeleton] get a shimmer overlay while their <img> children load.
  document.querySelectorAll('[data-skeleton]').forEach(el => {
    const img = el.tagName === 'IMG' ? el : el.querySelector('img');
    if (!img) { el.classList.add('skeleton'); return; }
    if (img.complete && img.naturalWidth) return; // already loaded
    el.classList.add('skeleton');
    img.addEventListener('load', () => el.classList.remove('skeleton'), {once: true});
    img.addEventListener('error', () => el.classList.remove('skeleton'), {once: true});
  });

  // ── Number counter animation ─────────────────────────────────────────────
  // Animates [data-count] elements from 0 up to their displayed integer value.
  const animateCounters = () => {
    document.querySelectorAll('[data-count]').forEach(el => {
      const target = parseInt(el.dataset.count, 10);
      if (isNaN(target) || target === 0) return;
      let start = null;
      const duration = 1200;
      const step = timestamp => {
        if (!start) start = timestamp;
        const progress = Math.min((timestamp - start) / duration, 1);
        // ease-out cubic
        const eased = 1 - Math.pow(1 - progress, 3);
        el.textContent = Math.round(eased * target);
        if (progress < 1) requestAnimationFrame(step);
        else el.textContent = target;
      };
      requestAnimationFrame(step);
    });
  };
  // Trigger counters when profile-stats enters the viewport.
  if ('IntersectionObserver' in window) {
    const statsEl = document.querySelector('.profile-stats');
    if (statsEl) {
      const counterObserver = new IntersectionObserver(entries => {
        if (entries[0].isIntersecting) { animateCounters(); counterObserver.disconnect(); }
      }, {threshold: 0.3});
      counterObserver.observe(statsEl);
    }
  }

  // Animate decorative icons, never move the user's click target.
  document.querySelectorAll('.primary, .category-row > a, .directory-card').forEach(control => {
    const icon = control.querySelector('.icon');
    const nudge = () => { if (finePointer.matches) play(icon, {x: [0, 4, 0], duration: 420}); };
    control.addEventListener('pointerenter', nudge);
    control.addEventListener('focus', () => play(icon, {scale: [1, 1.12, 1], duration: 350}));
  });

  // The visual selection responds instantly; server amounts are never tweened.
  document.querySelectorAll('input[name=seats]').forEach(input => input.addEventListener('change', () => {
    if (input.checked) play(input.parentElement, {scale: [.88, 1], ease: spring({stiffness: 260, damping: 17})});
  }));
  document.addEventListener('ticketly:selection', () => {
    play('#seat-total', {opacity: [.5, 1], y: [5, 0], duration: 250});
    play('.selected-item', {opacity: [0, 1], x: [10, 0], delay: stagger(25), duration: 300});
  });
  const navigation = document.getElementById('navigation');
  const menuButton = document.querySelector('.menu-button');
  menuButton?.addEventListener('click', () => {
    if (navigation.classList.contains('open')) play(navigation.querySelectorAll(':scope > a, :scope > details'), {opacity: [0, 1], x: [-8, 0], delay: stagger(35), duration: 280});
  });
  document.querySelector('.nav-help')?.addEventListener('toggle', function () {
    if (this.open) play(this.querySelectorAll('.help-menu a'), {opacity: [0, 1], y: [-5, 0], delay: stagger(30), duration: 220});
  });
  play('.success-check', {opacity: [0, 1], scale: [.65, 1], ease: spring({stiffness: 160, damping: 14})});
  play('.success-ticket', {opacity: [0, 1], y: [24, 0], rotate: [-2, 0], delay: 180, duration: 700});
  play('.message', {opacity: [0, 1], y: [-6, 0], duration: 280});

  // Auto-submit language switcher on <select> change (no button tap needed on mobile).
  document.querySelectorAll('.lang-form select').forEach(sel => {
    sel.addEventListener('change', () => sel.closest('form')?.submit());
  });

  // Disable active effects immediately if the preference changes or tab is hidden.
  reduced.addEventListener('change', () => { if (reduced.matches) stop(); });
  document.addEventListener('visibilitychange', () => { if (document.hidden) stop(); });
  window.addEventListener('pagehide', () => { stop(); observer?.disconnect(); });
  window.addEventListener('pageshow', event => { if (event.persisted) stop(); });
})();
