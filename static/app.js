document.addEventListener('DOMContentLoaded', () => {
  const seatForm = document.querySelector('#seat-form');
  if (seatForm) {
    const inputs = [...seatForm.querySelectorAll('input[name="seats"]')];
    const message = document.querySelector('#selection-message');
    function update() {
      const selected = inputs.filter(input => input.checked);
      document.querySelector('#seat-count').textContent = selected.length;
      document.querySelector('#seat-total').textContent = new Intl.NumberFormat('uz-UZ').format(selected.reduce((sum, input) => sum + Number(input.dataset.price), 0));
      const summary = document.querySelector('#selected-seats');
      if (summary) {
        summary.replaceChildren();
        if (!selected.length) summary.textContent = 'O‘rindiqlarni sxemadan tanlang.';
        selected.forEach(input => {
          const badge = document.createElement('span');
          badge.textContent = input.dataset.label;
          summary.appendChild(badge);
        });
      }
    }
    inputs.forEach(input => input.addEventListener('change', () => {
      message.textContent = '';
      if (inputs.filter(input => input.checked).length > 8) {
        input.checked = false;
        message.textContent = 'Bir bron uchun ko‘pi bilan 8 ta joy tanlang.';
      }
      update();
    }));
    const sector = document.querySelector('#sector-filter');
    const budget = document.querySelector('#seat-budget');
    function filter() {
      document.querySelectorAll('.sector').forEach(el => { el.hidden = el.dataset.sector !== sector.value; });
      document.querySelectorAll('.seat').forEach(el => {
        el.classList.toggle('over-budget', budget.value !== '' && Number(el.dataset.price) > Number(budget.value));
      });
    }
    sector.addEventListener('change', filter);
    budget.addEventListener('input', filter);
    seatForm.addEventListener('submit', event => {
      if (!inputs.some(input => input.checked)) {
        event.preventDefault();
        message.textContent = 'Avval kamida bitta o‘rindiq tanlang.';
      }
    });
    filter(); update();
    let refreshing = false;
    async function refreshAvailability() {
      if (document.hidden || refreshing || !seatForm.dataset.availability) return;
      refreshing = true;
      const status = document.querySelector('#availability-status');
      try {
        const response = await fetch(seatForm.dataset.availability, {headers: {'Accept': 'application/json'}});
        if (!response.ok) throw new Error('unavailable');
        const availability = new Map((await response.json()).map(seat => [String(seat.id), seat]));
        inputs.forEach(input => {
          const seat = availability.get(input.value);
          if (!seat) return;
          if (!seat.available && input.checked) {
            input.checked = false;
            message.textContent = 'Tanlangan joylardan biri band bo‘ldi. Boshqa joy tanlang.';
          }
          input.disabled = !seat.available;
          input.closest('.seat').classList.toggle('taken', !seat.available);
          input.dataset.price = seat.price;
          input.closest('.seat').dataset.price = seat.price;
        });
        if (status) status.textContent = '● Hozirgina yangilandi';
        filter(); update();
      } catch (_) {
        if (status) status.textContent = 'Mavjudlik qayta tekshirilmoqda';
      } finally { refreshing = false; }
    }
    setInterval(refreshAvailability, 15000);
  }
  document.querySelectorAll('[data-expires]').forEach(clock => {
    function tick() {
      const seconds = Math.max(0, Math.floor((new Date(clock.dataset.expires) - Date.now()) / 1000));
      clock.textContent = `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`;
      if (!seconds) {
        clock.textContent = 'Vaqt tugadi';
        document.querySelectorAll('.payment-form button').forEach(button => { button.disabled = true; });
      }
    }
    tick(); setInterval(tick, 1000);
  });
});
