import { api } from './api.js';
import { requireAuth } from './auth.js';
import { renderNavbar } from './navbar.js';
import { $, cell, currentMonth, el, emptyRow, money, setMessage, showFatal, showPage } from './utils.js';

let requestId = 0; // ignore out-of-date responses if the month changes quickly

function renderMonthOverMonth(mom) {
  const node = $('mom');
  if (mom.change_percent === null) {
    node.textContent = `No spend in ${mom.previous_month} to compare with`;
    node.className = 'mom mom-none';
  } else if (mom.change_amount === 0) {
    node.textContent = `No change vs ${mom.previous_month}`;
    node.className = 'mom mom-none';
  } else {
    const up = mom.change_amount > 0;
    const arrow = up ? '\u25B2' : '\u25BC';
    const sign = up ? '+' : '';
    node.textContent =
      `${arrow} ${sign}${mom.change_percent.toFixed(1)}% vs ${mom.previous_month} (${money.format(mom.previous_total)})`;
    node.className = `mom ${up ? 'mom-up' : 'mom-down'}`;
  }
}

function categoryRow(c) {
  return el('tr', {},
    el('td', {},
      el('div', { class: 'cat-name', text: c.category }),
      el('div', { class: 'bar', 'aria-hidden': 'true' },
        el('span', { style: `width: ${Math.min(100, c.share_percent)}%` }))),
    cell(money.format(c.total), 'num'),
    cell(`${c.share_percent.toFixed(1)}%`, 'num'));
}

function renderInsights(insights) {
  if (!insights.length) {
    $('insights').replaceChildren(
      el('p', { class: 'muted', text: 'No category is up sharply compared with last month.' }));
    return;
  }
  $('insights').replaceChildren(...insights.map((i) => el('div', { class: 'insight', text: i.message })));
}

async function loadSummary() {
  const month = $('month').value;
  if (!month) return;
  const id = ++requestId;
  try {
    const s = await api(`/summary?month=${encodeURIComponent(month)}`);
    if (id !== requestId) return;
    setMessage($('dashboard-message'), '');
    $('total').textContent = money.format(s.total_spend);
    $('all-time').textContent = money.format(s.all_time_total);
    renderMonthOverMonth(s.month_over_month);
    renderInsights(s.insights);
    const rows = s.by_category.map(categoryRow);
    $('by-category').replaceChildren(...(rows.length ? rows : [emptyRow('No expenses in this month yet.', 3)]));
  } catch (err) {
    if (id === requestId) setMessage($('dashboard-message'), err.message, 'error');
  }
}

async function main() {
  const user = await requireAuth();
  renderNavbar(user, '/dashboard');
  $('month').value = currentMonth();
  $('month').addEventListener('change', loadSummary);
  showPage();
  await loadSummary();
}

main().catch((err) => showFatal(err.message));
