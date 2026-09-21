import { api } from './api.js';
import { requireAuth } from './auth.js';
import { renderNavbar } from './navbar.js';
import { $, busy, el, setMessage, showFatal, showPage, todayISO } from './utils.js';

let messageTimer = null;

$('expense-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const message = $('form-message');
  const payload = {
    amount: $('amount').value,
    category: $('category').value,
    date: $('date').value,
    note: $('note').value,
  };

  await busy([$('add-btn')], async () => {
    clearTimeout(messageTimer);
    try {
      await api('/expenses', { method: 'POST', body: JSON.stringify(payload) });
      message.replaceChildren('Expense added. ', el('a', { class: 'link', href: '/expenses', text: 'View expenses' }));
      message.className = 'ok';
      // Keep date and category so several expenses can be entered quickly.
      $('amount').value = '';
      $('note').value = '';
      $('amount').focus();
      messageTimer = setTimeout(() => setMessage(message, ''), 6000);
    } catch (err) {
      setMessage(message, err.message, 'error');
    }
  });
});

async function main() {
  const user = await requireAuth();
  renderNavbar(user, '/add-expense');
  $('date').value = todayISO();
  $('date').max = todayISO(); // the API rejects future dates
  showPage();
  $('amount').focus();
}

main().catch((err) => showFatal(err.message));
