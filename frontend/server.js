// Serves the pages (html/), their styles (css/) and scripts (js/), and proxies /api/* to FastAPI.
// The proxy means the browser only talks to one origin, so no CORS setup is needed.
require('dotenv').config();
const path = require('path');
const express = require('express');

const PORT = process.env.PORT || 3000;
const BACKEND_URL = (process.env.BACKEND_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
const PUBLIC = path.join(__dirname, 'public');

const app = express();
app.use(express.json());

// ---------- API proxy ----------
app.use('/api', async (req, res) => {
  const headers = { 'Content-Type': 'application/json' };
  // Pass the user's JWT through to the backend untouched.
  if (req.headers.authorization) headers.Authorization = req.headers.authorization;

  const hasBody = !['GET', 'HEAD'].includes(req.method);
  try {
    // req.url is the path after "/api", including the query string.
    const upstream = await fetch(BACKEND_URL + req.url, {
      method: req.method,
      headers,
      body: hasBody ? JSON.stringify(req.body) : undefined,
    });
    const text = await upstream.text();
    res
      .status(upstream.status)
      .type(upstream.headers.get('content-type') || 'application/json')
      .send(text);
  } catch (err) {
    console.error('Backend request failed:', err.message);
    res.status(502).json({ error: 'bad_gateway', message: 'Backend is not reachable' });
  }
});

// ---------- static assets ----------
app.use('/css', express.static(path.join(PUBLIC, 'css')));
app.use('/js', express.static(path.join(PUBLIC, 'js')));
app.get('/favicon.svg', (req, res) => res.sendFile(path.join(PUBLIC, 'favicon.svg')));

// ---------- pages (clean URLs -> files in public/html) ----------
const PAGES = {
  '/login': 'login.html',
  '/register': 'register.html',
  '/dashboard': 'dashboard.html',
  '/expenses': 'expenses.html',
  '/add-expense': 'add-expense.html',
};
for (const [route, file] of Object.entries(PAGES)) {
  app.get(route, (req, res) => res.sendFile(path.join(PUBLIC, 'html', file)));
}
app.get('/', (req, res) => res.redirect('/dashboard')); // the page sends you to /login if needed

// ---------- errors ----------
app.use((req, res) => res.status(404).send('Page not found'));

// Malformed JSON from the browser should return JSON, not an HTML error page.
app.use((err, req, res, next) => {
  res.status(err.status || 500).json({ error: 'server_error', message: err.message });
});

app.listen(PORT, () => {
  console.log(`Frontend on http://localhost:${PORT} -> backend ${BACKEND_URL}`);
});
