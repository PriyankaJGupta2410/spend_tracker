// Builds the top navigation for every logged-in page.
import { logout } from './auth.js';
import { el } from './utils.js';

const LINKS = [
  ['/dashboard', 'Dashboard'],
  ['/expenses', 'Expenses'],
  ['/add-expense', 'Add expense'],
];

export function renderNavbar(user, activePath) {
  const header = document.getElementById('site-header');
  header.className = 'topbar';

  const links = LINKS.map(([href, label]) =>
    el('a', { href, class: 'nav-link', text: label, 'aria-current': href === activePath ? 'page' : null })
  );

  const logoutButton = el('button', { type: 'button', class: 'btn btn-secondary btn-small', text: 'Log out' });
  logoutButton.addEventListener('click', logout);

  header.replaceChildren(
    el('div', { class: 'topbar-inner' },
      el('a', { href: '/dashboard', class: 'brand' },
        el('img', { src: '/favicon.svg', alt: '', width: '28', height: '28' }),
        el('span', { text: 'Spend Tracker' })),
      el('nav', { class: 'nav-links', 'aria-label': 'Main' }, ...links),
      el('div', { class: 'nav-user' },
        el('span', { class: 'nav-username', text: user.username }),
        logoutButton))
  );
}
