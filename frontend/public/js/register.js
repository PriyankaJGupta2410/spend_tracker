import { login, redirectIfLoggedIn, register } from './auth.js';
import { $, busy, setMessage } from './utils.js';

const USERNAME_RULE = /^[A-Za-z0-9_]{3,30}$/;

/** Quick checks so the user gets instant feedback. The server validates again. */
function validate(username, password, confirm) {
  if (!USERNAME_RULE.test(username)) return 'Username must be 3 to 30 letters, numbers or underscores.';
  if (password.length < 8) return 'Password must be at least 8 characters.';
  if (new TextEncoder().encode(password).length > 72) return 'Password is too long (72 bytes at most).';
  if (password !== confirm) return 'Passwords do not match.';
  return null;
}

$('register-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const username = $('username').value.trim();
  const password = $('password').value;
  const message = $('register-message');

  const problem = validate(username, password, $('confirm').value);
  if (problem) {
    setMessage(message, problem, 'error');
    return;
  }

  await busy([$('register-btn')], async () => {
    try {
      await register(username, password);
    } catch (err) {
      setMessage(message, err.message, 'error'); // for example: username already taken
      return;
    }
    try {
      await login(username, password);
      window.location.href = '/dashboard';
    } catch (err) {
      setMessage(message, 'Account created. Please log in.', 'ok');
      setTimeout(() => { window.location.href = '/login'; }, 1200);
    }
  });
});

redirectIfLoggedIn();
