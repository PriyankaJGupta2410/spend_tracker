import { api } from './api.js';
import { requireAuth } from './auth.js';
import { renderNavbar } from './navbar.js';
import {
  $, cell, chipCell, el, emptyRow, money, monthStartISO, setMessage, showFatal, showPage, todayISO,
} from './utils.js';

const PAGE_SIZE = 20;
let offset = 0;    // how many rows are already on screen
let requestId = 0; // ignore out-of-date responses while the user is still typing

function expenseRow(e) {
  return el('tr', {}, cell(e.date), chipCell(e.category), cell(e.note || ''), cell(money.format(e.amount), 'num'));
}

/** Fetch one page of expenses. reset=true starts again from the first page. */
async function load({ reset }) {
  const from = $('from').value;
  const to = $('to').value;
  const category = $('category').value.trim();
  const message = $('expenses-message');

  if (from && to && from > to) {
    setMessage(message, '"From" must be on or before "To".', 'error');
    return;
  }
  setMessage(message, '');
  if (reset) offset = 0;

  const params = new URLSearchParams({ limit: PAGE_SIZE, offset });
  if (from) params.set('start_date', from);
  if (to) params.set('end_date', to);
  if (category) params.set('category', category);

  const id = ++requestId;
  try {
    const items = await api(`/expenses?${params}`);
    if (id !== requestId) return;

    const rows = items.map(expenseRow);
    if (reset) {
      const filtered = from || to || category;
      const emptyText = filtered ? 'No expenses match these filters.' : 'No expenses yet. Add your first one.';
      $('expenses').replaceChildren(...(rows.length ? rows : [emptyRow(emptyText, 4)]));
    } else {
      $('expenses').append(...rows);
    }
    offset += items.length;
    $('load-more').hidden = items.length < PAGE_SIZE;
    $('results-meta').textContent = offset ? `Showing ${offset} expense${offset === 1 ? '' : 's'}.` : '';
  } catch (err) {
    if (id === requestId) setMessage(message, err.message, 'error');
  }
}

function debounce(fn, ms) {
  let timer;
  return (...args) => { clearTimeout(timer); timer = setTimeout(() => fn(...args), ms); };
}

async function main() {
  const user = await requireAuth();
  renderNavbar(user, '/expenses');

  // Default view: this month so far.
  $('from').value = monthStartISO();
  $('to').value = todayISO();
  $('to').max = todayISO();

  $('from').addEventListener('change', () => load({ reset: true }));
  $('to').addEventListener('change', () => load({ reset: true }));
  $('category').addEventListener('input', debounce(() => load({ reset: true }), 250));
  $('filters').addEventListener('submit', (e) => e.preventDefault());
  $('load-more').addEventListener('click', () => load({ reset: false }));
  $('clear').addEventListener('click', () => {
    $('from').value = '';
    $('to').value = '';
    $('category').value = '';
    load({ reset: true });
  });

  showPage();
  await load({ reset: true });
}

main().catch((err) => showFatal(err.message));
