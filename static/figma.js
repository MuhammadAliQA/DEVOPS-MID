'use strict';
document.documentElement.classList.add('js-enabled');
const copy = JSON.parse(document.getElementById('ui-copy')?.textContent || '{}');
const t = (key, count) => (copy[key] || key).replace('{count}', count ?? '');
document.querySelector('.menu-button')?.addEventListener('click', function () {
  const open = this.getAttribute('aria-expanded') !== 'true';
  this.setAttribute('aria-expanded', String(open));
  document.getElementById('navigation').classList.toggle('open', open);
});
const closeNavigation = () => {
  document.querySelector('.menu-button')?.setAttribute('aria-expanded', 'false');
  document.getElementById('navigation')?.classList.remove('open');
  document.querySelectorAll('.nav-help[open]').forEach(menu => { menu.open = false; });
};
document.addEventListener('keydown', event => {
  if (event.key === 'Escape') {
    const help = document.querySelector('.nav-help[open]');
    if (help) { help.open = false; help.querySelector('summary').focus(); }
    else if (document.getElementById('navigation')?.classList.contains('open')) {
      closeNavigation(); document.querySelector('.menu-button')?.focus();
    }
  }
});
document.addEventListener('click', event => { if (!event.target.closest('.header')) closeNavigation(); });
window.matchMedia('(min-width: 1101px)').addEventListener('change', closeNavigation);
document.querySelector('.lang-form select')?.addEventListener('change', function () { this.form.requestSubmit(); });
document.querySelectorAll('img').forEach(img => img.addEventListener('error', () => {
  if (img.hasAttribute('data-directory-image')) {
    const parent = img.parentElement;
    parent.classList.add('portrait-placeholder');
    const initial = document.createElement('span'); initial.textContent = img.alt.slice(0, 1); initial.setAttribute('aria-hidden', 'true');
    img.replaceWith(initial); return;
  }
  if (!img.classList.contains('real-qr') && !img.dataset.fallback) {
    img.dataset.fallback = 'true'; img.src = '/static/figma-favicon.png'; img.classList.add('empty-image');
  }
}));
const seatForm = document.getElementById('seat-form');
if (seatForm) {
  const inputs = [...seatForm.querySelectorAll('input[name=seats]')];
  const notice = document.getElementById('seat-notice');
  let selectionSignature = '';
  const render = () => {
    const chosen = inputs.filter(input => input.checked);
    document.getElementById('selection-heading').textContent = chosen.length ? t('selected_count', chosen.length) : t('no_seats');
    document.getElementById('reserve-button').disabled = !chosen.length;
    document.getElementById('seat-total').textContent = new Intl.NumberFormat(document.documentElement.lang).format(chosen.reduce((sum, item) => sum + Number(item.dataset.price), 0)) + ' UZS';
    const signature = chosen.map(input => input.value).join(',');
    if (signature === selectionSignature) return;
    selectionSignature = signature;
    const list = document.getElementById('selected-list'); list.replaceChildren();
    chosen.forEach(input => {
      const row = document.createElement('div'); row.className = 'selected-item';
      const label = document.createElement('span'); label.textContent = input.dataset.label;
      const price = document.createElement('b'); price.textContent = Number(input.dataset.price).toLocaleString() + ' UZS';
      const remove = document.createElement('button'); remove.type = 'button'; remove.textContent = '×'; remove.setAttribute('aria-label', input.dataset.label + ' ×');
      remove.onclick = () => { input.checked = false; render(); };
      row.append(label, price, remove); list.append(row);
    });
    document.dispatchEvent(new CustomEvent('ticketly:selection'));
  };
  inputs.forEach(input => input.addEventListener('change', () => {
    if (inputs.filter(item => item.checked).length > 8) { input.checked = false; notice.textContent = t('seat_limit'); }
    render();
  }));
  render();
  document.getElementById('sector-filter')?.addEventListener('change', function () {
    seatForm.querySelectorAll('[data-sector]').forEach(section => { section.hidden = !!this.value && section.dataset.sector !== this.value; });
  });
  document.getElementById('seat-budget')?.addEventListener('input', function () {
    inputs.forEach(input => input.parentElement.classList.toggle('over-budget', this.value !== '' && Number(input.dataset.price) > Number(this.value)));
  });
  let stopped = false;
  window.addEventListener('pagehide', () => { stopped = true; });
  const poll = async () => {
    if (stopped) return;
    try {
      const response = await fetch(seatForm.dataset.availability, {headers: {'Accept': 'application/json'}, signal: AbortSignal.timeout(8000)});
      if (!response.ok) throw Error('availability');
      const seats = await response.json();
      for (const seat of seats) {
        const input = inputs.find(item => Number(item.value) === seat.id);
        if (!input) continue;
        if (!seat.available && input.checked) { input.checked = false; notice.textContent = t('seat_taken'); }
        input.disabled = !seat.available;
        input.parentElement.classList.toggle('occupied', !seat.available);
      }
      render();
    } catch (_) { notice.textContent = t('retrying'); }
    if (!stopped) setTimeout(poll, 5000);
  };
  setTimeout(poll, 5000);
}
document.querySelectorAll('[data-expires]').forEach(node => {
  const update = () => {
    const seconds = Math.max(0, Math.ceil((Date.parse(node.dataset.expires) - Date.now()) / 1000));
    node.textContent = seconds ? `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}` : t('expired');
    if (!seconds) document.querySelectorAll('.checkout-layout button').forEach(button => { button.disabled = true; });
  };
  update(); setInterval(update, 1000);
});
