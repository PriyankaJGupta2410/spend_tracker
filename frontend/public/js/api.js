// Talks to the backend through the Express proxy (/api/*) and stores the JWT.

const TOKEN_KEY = 'spend_tracker_token';

// The JWT lives in localStorage for simplicity (see README for the safer HttpOnly cookie option).
export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const setToken = (token) => localStorage.setItem(TOKEN_KEY, token);
export const clearToken = () => localStorage.removeItem(TOKEN_KEY);

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

function describeError(data, status) {
  if (data && Array.isArray(data.details) && data.details.length) {
    return data.details.map((d) => `${d.field}: ${d.message}`).join('; ');
  }
  return (data && data.message) || `Request failed (${status})`;
}

/**
 * Call the API. By default a 401 means the session is over: the token is cleared and the browser
 * goes to the login page. In that case the returned promise never settles, which conveniently
 * stops the page script that was waiting for data. Login and register pass
 * { redirectOn401: false } because a 401 there just means "wrong password".
 */
export async function api(path, options = {}, { redirectOn401 = true } = {}) {
  const headers = { 'Content-Type': 'application/json' };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  let res;
  try {
    res = await fetch('/api' + path, { ...options, headers });
  } catch (_) {
    throw new ApiError('Cannot reach the server. Check your connection and try again.', 0);
  }

  let data = null;
  try { data = await res.json(); } catch (_) { /* non-JSON body */ }

  if (res.status === 401 && redirectOn401) {
    clearToken();
    window.location.replace('/login?expired=1');
    return new Promise(() => {});
  }
  if (!res.ok) throw new ApiError(describeError(data, res.status), res.status);
  return data;
}
