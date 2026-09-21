import { login, redirectIfLoggedIn } from './auth.js';
import { $, busy, setMessage } from './utils.js';

// Shown when the API told us the token expired.
if (new URLSearchParams(window.location.search).has('expired')) {
  $('expired-notice').hidden = false;
}

$('login-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const username = $('username').value.trim();
  const password = $('password').value;
  const message = $('login-message');

  if (!username || !password) {
    setMessage(message, 'Enter your username and password.', 'error');
    return;
  }

  await busy([$('login-btn')], async () => {
    try {
      await login(username, password);
      window.location.href = '/dashboard';
    } catch (err) {
      setMessage(message, err.message, 'error');
    }
  });
});

redirectIfLoggedIn();
