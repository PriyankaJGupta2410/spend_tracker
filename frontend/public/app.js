const CURRENCY = 'INR';
const TOKEN_KEY = 'spend_tracker_token';
const money = new Intl.NumberFormat('en-IN', { style: 'currency', currency: CURRENCY });
const $ = (id) => document.getElementById(id);

// The JWT is kept in localStorage for simplicity (see README for the safer cookie option).
let token = localStorage.getItem(TOKEN_KEY);
let formMessageTimer = null;

function pad(n) { return String(n).padStart(2, '0'); }
function todayISO() {
  const d = new Date();
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

// ---------- API helper ----------

async function api(path, options = {}, { expireOn401 = true } = {}) {
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch('/api' + path, { ...options, headers });
  let data = null;
  try { data = await res.json(); } catch (_) { /* non-JSON body */ }
  if (res.status === 401 && expireOn401) {
    logout();
    throw new Error('Your session has expired. Please log in again.');
  }
  if (!res.ok) throw new Error(describeError(data, res.status));
  return data;
}

function describeError(data, status) {
  if (data && Array.isArray(data.details) && data.details.length) {
    return data.details.map((d) => `${d.field}: ${d.message}`).join('; ');
  }
  return (data && data.message) || `Request failed (${status})`;
}

function setMessage(el, text, kind) {
  el.textContent = text;
  el.className = kind || '';
}

// Disable buttons while a request is running so nothing gets submitted twice.
async function busy(buttons, fn) {
  buttons.forEach((b) => { b.disabled = true; });
  try {
    return await fn();
  } finally {
    buttons.forEach((b) => { b.disabled = false; });
  }
}

// ---------- auth ----------

function showAuth() {
  $('app').hidden = true;
  $('auth-section').hidden = false;
}

async function showApp() {
  const me = await api('/auth/me');
  $('whoami').textContent = me.username;
  $('auth-section').hidden = true;
  $('app').hidden = false;
  await refresh();
}

function logout() {
  token = null;
  localStorage.removeItem(TOKEN_KEY);
  showAuth();
}

async function login(username, password) {
  const data = await api('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  }, { expireOn401: false });
  token = data.access_token;
  localStorage.setItem(TOKEN_KEY, token);
  await showApp();
}

const authButtons = () => [$('login-btn'), $('register-btn')];

$('auth-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  await busy(authButtons(), async () => {
    try {
      await login($('username').value, $('password').value);
      $('password').value = '';
      setMessage($('auth-message'), '');
    } catch (err) {
      setMessage($('auth-message'), err.message, 'error');
    }
  });
});

$('register-btn').addEventListener('click', async () => {
  const username = $('username').value;
  const password = $('password').value;
  await busy(authButtons(), async () => {
    try {
      await api('/auth/register', {
        method: 'POST',
        body: JSON.stringify({ username, password }),
      }, { expireOn401: false });
      await login(username, password);
      $('password').value = '';
      setMessage($('auth-message'), '');
    } catch (err) {
      setMessage($('auth-message'), err.message, 'error');
    }
  });
});

$('logout').addEventListener('click', logout);

// ---------- rendering helpers ----------
// Everything is built with textContent, never innerHTML, so user text cannot inject markup.

function cell(text, className) {
  const td = document.createElement('td');
  td.textContent = text;
  if (className) td.className = className;
  return td;
}

function chipCell(text) {
  const td = document.createElement('td');
  const chip = document.createElement('span');
  chip.className = 'chip';
  chip.textContent = text;
  td.append(chip);
  return td;
}

function emptyRow(text, columns) {
  const tr = document.createElement('tr');
  const td = cell(text, 'empty');
  td.colSpan = columns;
  tr.append(td);
  return tr;
}

function categoryRow(c) {
  const tr = document.createElement('tr');

  const nameTd = document.createElement('td');
  const name = document.createElement('div');
  name.className = 'cat-name';
  name.textContent = c.category;
  const bar = document.createElement('div');
  bar.className = 'bar';
  bar.setAttribute('aria-hidden', 'true');
  const fill = document.createElement('span');
  fill.style.width = `${Math.min(100, c.share_percent)}%`;
  bar.append(fill);
  nameTd.append(name, bar);

  tr.append(nameTd, cell(money.format(c.total), 'num'), cell(`${c.share_percent.toFixed(1)}%`, 'num'));
  return tr;
}

function monthBounds(value) {
  const [y, m] = value.split('-').map(Number);
  const last = new Date(y, m, 0).getDate();
  return { start: `${y}-${pad(m)}-01`, end: `${y}-${pad(m)}-${pad(last)}` };
}

function renderMonthOverMonth(mom) {
  const el = $('mom');
  if (mom.change_percent === null) {
    el.textContent = `No spend in ${mom.previous_month} to compare with`;
    el.className = 'mom mom-none';
  } else if (mom.change_amount === 0) {
    el.textContent = `No change vs ${mom.previous_month}`;
    el.className = 'mom mom-none';
  } else {
    const up = mom.change_amount > 0;
    const arrow = up ? '\u25B2' : '\u25BC';
    const sign = up ? '+' : '';
    el.textContent =
      `${arrow} ${sign}${mom.change_percent.toFixed(1)}% vs ${mom.previous_month} (${money.format(mom.previous_total)})`;
    el.className = `mom ${up ? 'mom-up' : 'mom-down'}`;
  }
}

// ---------- summary and list ----------

async function loadSummary() {
  const month = $('month').value;
  if (!month) return;
  try {
    const s = await api(`/summary?month=${encodeURIComponent(month)}`);
    setMessage($('summary-message'), '');
    $('total').textContent = money.format(s.total_spend);
    $('all-time').textContent = money.format(s.all_time_total);
    renderMonthOverMonth(s.month_over_month);

    $('insights').replaceChildren(...s.insights.map((i) => {
      const div = document.createElement('div');
      div.className = 'insight';
      div.textContent = i.message;
      return div;
    }));

    const rows = s.by_category.map(categoryRow);
    $('by-category').replaceChildren(
      ...(rows.length ? rows : [emptyRow('No expenses in this month yet.', 3)])
    );
  } catch (err) {
    setMessage($('summary-message'), err.message, 'error');
  }
}

async function loadExpenses() {
  const month = $('month').value;
  if (!month) return;
  const { start, end } = monthBounds(month);
  const params = new URLSearchParams({ start_date: start, end_date: end });
  const category = $('filter-category').value.trim();
  if (category) params.set('category', category);
  try {
    const items = await api(`/expenses?${params}`);
    const rows = items.map((e) => {
      const tr = document.createElement('tr');
      tr.append(cell(e.date), chipCell(e.category), cell(e.note || ''), cell(money.format(e.amount), 'num'));
      return tr;
    });
    const emptyText = category
      ? 'No expenses match this category.'
      : 'No expenses this month yet. Add one above.';
    $('expenses').replaceChildren(...(rows.length ? rows : [emptyRow(emptyText, 4)]));
  } catch (err) {
    setMessage($('summary-message'), err.message, 'error');
  }
}

function refresh() { return Promise.all([loadSummary(), loadExpenses()]); }

$('expense-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const payload = {
    amount: $('amount').value,
    category: $('category').value,
    date: $('date').value,
    note: $('note').value,
  };
  await busy([$('add-btn')], async () => {
    try {
      await api('/expenses', { method: 'POST', body: JSON.stringify(payload) });
      setMessage($('form-message'), 'Expense added.', 'ok');
      clearTimeout(formMessageTimer);
      formMessageTimer = setTimeout(() => setMessage($('form-message'), ''), 3000);
      $('amount').value = '';
      $('note').value = '';
      // Jump to the month of the new expense so the user sees it reflected.
      $('month').value = payload.date.slice(0, 7);
      await refresh();
    } catch (err) {
      clearTimeout(formMessageTimer);
      setMessage($('form-message'), err.message, 'error');
    }
  });
});

$('month').addEventListener('change', refresh);
$('filter-category').addEventListener('input', loadExpenses);

// ---------- start ----------

$('date').value = todayISO();
$('date').max = todayISO(); // the API rejects future dates
$('month').value = todayISO().slice(0, 7);
if (token) {
  showApp().catch(showAuth);
} else {
  showAuth();
}