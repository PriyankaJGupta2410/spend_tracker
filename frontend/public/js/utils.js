// Small helpers shared by every page.

export const CURRENCY = 'INR';
export const money = new Intl.NumberFormat('en-IN', { style: 'currency', currency: CURRENCY });

export const $ = (id) => document.getElementById(id);

export function pad(n) { return String(n).padStart(2, '0'); }

export function todayISO() {
  const d = new Date();
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}
export function currentMonth() { return todayISO().slice(0, 7); }
export function monthStartISO() { return `${currentMonth()}-01`; }

/** Create an element. Children and `text` are inserted as text, never as HTML, so user data is safe. */
export function el(tag, props = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (value === undefined || value === null) continue;
    if (key === 'class') node.className = value;
    else if (key === 'text') node.textContent = value;
    else node.setAttribute(key, value);
  }
  node.append(...children);
  return node;
}

export function setMessage(node, text, kind = '') {
  node.textContent = text;
  node.className = kind;
}

/** Disable buttons while a request runs so nothing is submitted twice. */
export async function busy(buttons, fn) {
  buttons.forEach((b) => { b.disabled = true; });
  try {
    return await fn();
  } finally {
    buttons.forEach((b) => { b.disabled = false; });
  }
}

// ----- table helpers -----
export const cell = (text, className) => el('td', { class: className, text });

export const chipCell = (text) => el('td', {}, el('span', { class: 'chip', text }));

export function emptyRow(text, columns) {
  return el('tr', {}, el('td', { class: 'empty', colspan: String(columns), text }));
}

// ----- page state -----
/** Pages start hidden so nothing flashes before we know the user is logged in. */
export function showPage() { $('page').hidden = false; }

export function showFatal(message) {
  showPage();
  document.body.prepend(el('div', { class: 'banner', role: 'alert', text: message }));
}
