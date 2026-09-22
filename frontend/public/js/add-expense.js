import { api } from './api.js';
import { requireAuth } from './auth.js';
import { renderNavbar } from './navbar.js';
import { $, busy, el, setMessage, showFatal, showPage, todayISO } from './utils.js';

let messageTimer = null;
let closeCategoryDropdown = () => {}; // replaced once the combobox is wired up

/** A small, fully custom combobox: styled and keyboard-navigable the same way in every browser,
 * unlike a native <input list> + <datalist>, which Safari barely supports and none let us style. */
function wireCategoryCombo(categories) {
  const wrap = $('category-combo');
  const input = $('category');
  const toggle = $('category-toggle');
  const list = $('category-listbox');
  let items = [];       // categories currently rendered, after filtering by what's typed
  let activeIndex = -1; // keyboard-highlighted row; -1 means none highlighted

  function matches(query) {
    const q = query.trim().toLowerCase();
    return q ? categories.filter((c) => c.toLowerCase().includes(q)) : categories;
  }

  function render(query) {
    items = matches(query);
    activeIndex = -1;
    list.replaceChildren();
    if (items.length) {
      items.forEach((category, i) => list.append(el('li', {
        id: `category-option-${i}`, class: 'combo-option', role: 'option', 'aria-selected': 'false', text: category,
      })));
    } else {
      list.append(el('li', {
        class: 'combo-empty', role: 'presentation',
        text: categories.length ? 'No matching categories \u2014 keep typing to add a new one.'
                                 : 'No categories yet \u2014 type to create your first one.',
      }));
    }
  }

  function setActive(index) {
    activeIndex = index;
    [...list.children].forEach((li, i) => {
      const isActive = i === index && li.classList.contains('combo-option');
      li.classList.toggle('is-active', isActive);
      if (li.classList.contains('combo-option')) li.setAttribute('aria-selected', String(isActive));
    });
    if (items[index]) input.setAttribute('aria-activedescendant', `category-option-${index}`);
    else input.removeAttribute('aria-activedescendant');
  }

  function open() {
    if (!wrap.classList.contains('open')) render(input.value);
    wrap.classList.add('open');
    list.hidden = false;
    input.setAttribute('aria-expanded', 'true');
  }

  function close() {
    wrap.classList.remove('open');
    list.hidden = true;
    input.setAttribute('aria-expanded', 'false');
    input.removeAttribute('aria-activedescendant');
    activeIndex = -1;
  }
  closeCategoryDropdown = close;

  function choose(index) {
    if (!items[index]) return;
    input.value = items[index];
    close();
    input.focus();
  }

  input.addEventListener('input', () => { render(input.value); open(); });
  input.addEventListener('focus', open);
  input.addEventListener('keydown', (event) => {
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      wrap.classList.contains('open') ? setActive(Math.min(activeIndex + 1, items.length - 1)) : open();
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      wrap.classList.contains('open') ? setActive(Math.max(activeIndex - 1, 0)) : open();
    } else if (event.key === 'Enter' && wrap.classList.contains('open') && activeIndex >= 0) {
      event.preventDefault();
      choose(activeIndex);
    } else if (event.key === 'Escape' && wrap.classList.contains('open')) {
      close();
    }
  });

  // mousedown (not click) fires before the input's blur, so the click registers before the list disappears.
  list.addEventListener('mousedown', (event) => {
    const li = event.target.closest('.combo-option');
    if (!li) return;
    event.preventDefault();
    choose([...list.children].indexOf(li));
  });

  toggle.addEventListener('click', () => {
    if (wrap.classList.contains('open')) close();
    else open();
    input.focus();
  });

  document.addEventListener('click', (event) => {
    if (!wrap.contains(event.target)) close();
  });
}

/** Fetch the user's existing categories once, show a hint, and wire up the combobox with them. */
async function loadCategoryOptions() {
  const hint = $('category-hint');
  let categories = [];
  try {
    categories = await api('/expenses/categories');
  } catch (_) {
    // Suggestions are a nice-to-have; the combobox still works for free-text entry without them.
  }
  hint.textContent = categories.length
    ? `Choose from ${categories.length} categor${categories.length === 1 ? 'y' : 'ies'} you\u2019ve used before, or type a new one.`
    : 'Type a category \u2014 it\u2019ll be suggested next time.';
  wireCategoryCombo(categories);
}

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
      closeCategoryDropdown();
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
  loadCategoryOptions();
  showPage();
  $('amount').focus();
}

main().catch((err) => showFatal(err.message));