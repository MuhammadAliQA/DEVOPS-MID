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

  // Reveal only when content enters the viewport; no hidden-content prerequisite.
  let observer;
  if ('IntersectionObserver' in window) {
    observer = new IntersectionObserver(entries => {
      const visible = entries.filter(entry => entry.isIntersecting);
      play(visible.map(entry => entry.target), {opacity: [0, 1], y: [20, 0], delay: stagger(55, {start: 0}), duration: 620});
      visible.forEach(entry => observer.unobserve(entry.target));
    }, {threshold: .07});
    document.querySelectorAll('.section-title, .event-card, .directory-card, .venue-card, .form-card, .order-card, .digital-ticket, .support-layout, .profile-hero').forEach(element => observer.observe(element));
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

  // Disable active effects immediately if the preference changes or tab is hidden.
  reduced.addEventListener('change', () => { if (reduced.matches) stop(); });
  document.addEventListener('visibilitychange', () => { if (document.hidden) stop(); });
  window.addEventListener('pagehide', () => { stop(); observer?.disconnect(); });
  window.addEventListener('pageshow', event => { if (event.persisted) stop(); });
})();
