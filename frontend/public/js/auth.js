// Login, register, logout and the guards that protect pages.
import { api, ApiError, clearToken, getToken, setToken } from './api.js';

export async function register(username, password) {
  return api('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  }, { redirectOn401: false });
}

export async function login(username, password) {
  const data = await api('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  }, { redirectOn401: false });
  setToken(data.access_token);
}

export function logout() {
  clearToken();
  window.location.replace('/login');
}

/** For protected pages: returns the current user, or sends the browser to /login. */
export async function requireAuth() {
  if (!getToken()) {
    window.location.replace('/login');
    return new Promise(() => {}); // never resolves, the page is navigating away
  }
  return api('/auth/me'); // a 401 here redirects to /login by itself
}

/** For login and register: if you are already logged in, go straight to the dashboard. */
export async function redirectIfLoggedIn() {
  if (!getToken()) return;
  try {
    await api('/auth/me', {}, { redirectOn401: false });
    window.location.replace('/dashboard');
  } catch (err) {
    if (err instanceof ApiError && err.status === 401) clearToken();
  }
}
