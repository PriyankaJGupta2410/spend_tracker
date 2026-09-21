# Spend Tracker

A small expense tracking service. Users register and log in, log their own expenses, filter them, and get a monthly summary with month-over-month change and a simple spending insight.

- **Backend:** Python, FastAPI (built on Starlette), Pydantic v2, SQLAlchemy 2.0, MySQL
- **Auth:** JWT bearer tokens (PyJWT) with bcrypt password hashing
- **Config:** `.env` files
- **Frontend:** plain HTML, CSS and JavaScript, served by a small Express server (`server.js`)

```
spend-tracker/
├── backend/
│   ├── app/
│   │   ├── main.py        # routes, error handlers, CORS (Starlette middleware)
│   │   ├── config.py      # loads .env and exposes settings
│   │   ├── database.py    # SQLAlchemy engine and session dependency
│   │   ├── models.py      # User and Expense tables
│   │   ├── schemas.py     # Pydantic request/response models and validation
│   │   ├── auth.py        # bcrypt hashing, JWT creation and verification
│   │   └── services.py    # queries and business logic (summary, MoM, insights)
│   ├── tests/             # pytest suite
│   ├── .env.example
│   └── requirements.txt
├── frontend/
│   ├── server.js          # Express: page routes, static files, /api proxy to the backend
│   ├── package.json
│   ├── .env.example
│   └── public/
│       ├── html/          # one file per page: login, register, dashboard, expenses, add-expense
│       ├── css/           # base.css and navbar.css (shared) + one css file per page
│       ├── js/            # api, auth, utils, navbar (shared) + one js file per page
│       └── favicon.svg
└── README.md
```

## Run it locally

Requirements: Python 3.10+, Node.js 18+, and a running MySQL 8 server (MariaDB 10.5+ also works).

### 1. Database

Create the database. The tables are created automatically when the backend starts.

```sql
CREATE DATABASE spend_tracker CHARACTER SET utf8mb4;
```

If you ran an earlier version of this project against the same database, drop it and recreate it, because the schema now has a `users` table and `expenses.user_id`.

### 2. Backend

```bash
cd backend
cp .env.example .env               # then edit .env (see below)
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

API docs (Swagger UI) are at http://localhost:8000/docs. Use the **Authorize** button and paste the `access_token` from `/auth/login` to try the protected routes.

### 3. Frontend

In a second terminal:

```bash
cd frontend
cp .env.example .env
npm install
npm start
```

Open http://localhost:3000, create an account and start adding expenses.

| Page | URL | Files |
|---|---|---|
| Log in | `/login` | `html/login.html`, `css/login.css`, `js/login.js` |
| Create account | `/register` | `html/register.html`, `css/register.css`, `js/register.js` |
| Dashboard (summary, month-over-month, insights) | `/dashboard` | `html/dashboard.html`, `css/dashboard.css`, `js/dashboard.js` |
| Expenses (date range and category filters, load more) | `/expenses` | `html/expenses.html`, `css/expenses.css`, `js/expenses.js` |
| Add expense | `/add-expense` | `html/add-expense.html`, `css/add-expense.css`, `js/add-expense.js` |

Every page also loads the shared `css/base.css` (theme and common components). The logged-in pages add `css/navbar.css` and `js/navbar.js`. Shared scripts: `js/api.js` (fetch wrapper and token storage), `js/auth.js` (login, register, logout and page guards) and `js/utils.js` (formatting and DOM helpers). Scripts are ES modules, so no build step is needed.

### 4. Tests

```bash
cd backend
pytest
```

By default the tests run against a throwaway SQLite file, so they need no setup. To run them against real MySQL (recommended before shipping), create a separate test database with `CREATE DATABASE spend_tracker_test CHARACTER SET utf8mb4;`, then:

```bash
TEST_DATABASE_URL="mysql+pymysql://root:password@127.0.0.1:3306/spend_tracker_test?charset=utf8mb4" pytest
```

The test tables are dropped and recreated around every test, so never point `TEST_DATABASE_URL` at real data.

## Configuration (`.env`)

Settings are read from `backend/.env` (loaded by `python-dotenv`). Real environment variables take priority over the file, which is how hosting platforms usually inject them. The app refuses to start if `DATABASE_URL` or `JWT_SECRET_KEY` is missing.

**`backend/.env`**

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | required | `mysql+pymysql://USER:PASSWORD@HOST:PORT/DATABASE?charset=utf8mb4` |
| `JWT_SECRET_KEY` | required | Long random string used to sign tokens |
| `JWT_ALGORITHM` | `HS256` | Signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Token lifetime |
| `CORS_ORIGINS` | `*` | Comma-separated origins allowed to call the API from a browser |
| `BCRYPT_ROUNDS` | `12` | Password hashing cost (only lowered in tests) |

Generate a secret with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

**`frontend/.env`**

| Variable | Default | Purpose |
|---|---|---|
| `PORT` | `3000` | Express port |
| `BACKEND_URL` | `http://127.0.0.1:8000` | Where the proxy forwards `/api/*` |

`.env` is in `.gitignore`. Commit only the `.env.example` files.

## API

Public routes: `/health`, `/auth/register`, `/auth/login`. Everything else needs the header `Authorization: Bearer <token>`.

### `POST /auth/register`

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "priyanka", "password": "a-strong-password"}'
```

Returns `201` with `{"id": 1, "username": "priyanka"}`. Usernames are 3 to 30 letters, digits or underscores, stored lowercase. Passwords are 8 to 72 bytes. A taken username returns `409`.

### `POST /auth/login`

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "priyanka", "password": "a-strong-password"}'
```

Returns `{"access_token": "...", "token_type": "bearer", "expires_in": 3600}`. Wrong password and unknown username both return the same `401` message, so the endpoint does not reveal which usernames exist.

### `GET /auth/me`

Returns the current user. The UI uses it to check a saved token on page load.

### `POST /expenses`

```bash
curl -X POST http://localhost:8000/expenses \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"amount": "249.50", "category": "Food", "note": "lunch", "date": "2026-09-01"}'
```

Returns `201` with the stored expense. Rules:

- `amount`: greater than 0, at most 2 decimal places, at most 10 digits
- `category`: 1 to 50 characters after trimming, stored lowercase
- `note`: optional, up to 200 characters
- `date`: `YYYY-MM-DD`, not in the future

### `GET /expenses`

Query parameters, all optional: `category`, `start_date`, `end_date` (inclusive), `limit` (1 to 500, default 100), `offset`. Results are newest first and only include the logged-in user's expenses. `start_date` after `end_date` returns `422`.

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/expenses?category=food&start_date=2026-09-01&end_date=2026-09-30"
```

### `GET /summary?month=YYYY-MM`

`month` is optional and defaults to the current month.

```json
{
  "month": "2026-09",
  "total_spend": 350.25,
  "all_time_total": 1349.25,
  "by_category": [{"category": "travel", "total": 200.0, "share_percent": 57.1}],
  "month_over_month": {
    "previous_month": "2026-08",
    "previous_total": 100.0,
    "change_amount": 250.25,
    "change_percent": 250.25
  },
  "insights": [
    {"category": "food", "previous": 100.0, "current": 130.0, "change_percent": 30.0,
     "message": "Food spend rose 30.0% vs 2026-08 (100.00 to 130.00)."}
  ]
}
```

### Errors

All errors share one shape:

```json
{"error": "validation_error", "message": "Invalid request",
 "details": [{"field": "amount", "message": "Input should be greater than 0"}]}
```

| Status | When |
|---|---|
| 201 | Expense or user created |
| 401 | Missing, invalid or expired token, or wrong login credentials |
| 409 | Username already taken |
| 422 | Invalid body or query parameters, or a reversed date range |

## Key design decisions

- **MySQL through SQLAlchemy 2.0.** The models in `models.py` define the schema, `create_all` creates the tables on startup, and every request gets its own `Session` from a FastAPI dependency that always closes it. The engine is a plain module-level object in `database.py`, and it uses `pool_pre_ping` and `pool_recycle` because MySQL drops idle connections.
- **Money as `DECIMAL(12, 2)`.** Fixed-point in the database and `Decimal` in Python, so `0.1 + 0.2` is exactly `0.30` and `SUM()` is exact. Input with more than two decimal places is rejected instead of silently rounded. Amounts become JSON numbers only at the response edge.
- **Real `DATE` column and composite indexes.** Range filters and monthly grouping are plain `>=` and `<` comparisons. Indexes on `(user_id, spent_on)` and `(user_id, category, spent_on)` match how every query is filtered. A `CHECK (amount > 0)` constraint backs up the API validation (enforced by MySQL 8.0.16 and later).
- **JWT authentication.** Login returns a signed, expiring token whose `sub` is the user id. On each request the token is verified with a fixed algorithm list, `exp` and `sub` are required, and the user is loaded from the database, so a token for a deleted user stops working. The secret comes from `.env`.
- **Passwords with bcrypt.** Only the hash is stored. Login always performs a bcrypt check (against a dummy hash when the username is unknown) and returns one generic error, to avoid revealing which usernames exist through the message or the response time.
- **Per-user data.** Every expense has a `user_id` foreign key, and every query in `services.py` filters by it. A test confirms that one user never sees another's expenses or summary.
- **Categories are normalised** (trimmed, lowercased) on the way in, so "Food" and "food " are the same bucket. Filtering is normalised the same way.
- **Summary is scoped to a month.** Month-over-month needs a reference month, so total and category breakdown are for the chosen month, compared with the previous one. `all_time_total` is included as an extra figure. When the previous month has no spend, `change_percent` is `null` rather than infinity or a made-up number.
- **Spike insight rules.** A category is flagged when spend is *strictly more than* 20% above last month. Categories with no spend last month are not flagged, because there is no baseline. The threshold is a constant in `services.py`.
- **Separated layers.** `main.py` handles HTTP, `schemas.py` validation, `models.py` and `database.py` persistence, `auth.py` security, and `services.py` the queries and pure calculation functions (`compute_change`, `find_spikes`, `month_range`), which are unit tested without HTTP.
- **Consistent error responses.** Starlette exception handlers convert Pydantic validation errors and `HTTPException`s into one JSON shape, so a client only has to handle one format.
- **Express serves pages and proxies the API.** It maps clean URLs (`/login`, `/dashboard` and so on) to the files in `public/html`, serves `css/` and `js/` as static assets, and forwards `/api/*` to FastAPI with the `Authorization` header passed through. The browser only talks to one origin, so no CORS setup is needed.
- **Frontend guards and safety.** Logged-in pages stay hidden until `/auth/me` confirms the token, and any 401 clears the token and returns to `/login`. All user text is inserted with `textContent`, so a note like `<script>` cannot inject markup.

## Testing

58 tests in `backend/tests/`, each running against an empty database. They pass on both SQLite and MySQL-compatible MariaDB 10.11.

- **Expenses:** creation and normalisation, persistence, a parametrised set of 10 invalid payloads (negative, zero, too many decimals, blank category, future date and so on), no write on invalid input, category and date filters, inclusive range boundaries, reversed range, pagination.
- **Summary:** per-month totals that do not leak across months, category shares, month-over-month, empty database, no previous data, January to December rollover, the exact 20% boundary of the insight, floating point drift, invalid `month` values.
- **Auth:** registration rules, duplicate usernames, hashed storage, login success and identical failure responses, all protected routes without a token, garbage token, wrong-secret token, expired token, token without `exp`, token for a nonexistent user, and isolation between two users.

## What I would do differently with more time

- Use **Alembic migrations** instead of `create_all`, so schema changes are versioned and reversible.
- Add **refresh tokens** and token revocation (logout on the server), and store the token in an **HttpOnly, SameSite cookie** instead of `localStorage`, which JavaScript on the page can read.
- Add **rate limiting** on `/auth/login` to slow down password guessing.
- Add **update and delete** endpoints, plus a `total` count and cursor pagination on the list endpoint.
- Support **multiple currencies** (a currency column and per-currency summaries) and a user timezone, since "current month" is currently based on the server date.
- Make the insight threshold a query parameter, and add a budget per category.
- Add **frontend tests**, CI running `pytest`, and a health check that also pings the database.

## Deployment notes (bonus)

Two web services plus a managed MySQL database on Render, Railway, Fly.io or similar:

1. **Database:** provision MySQL (Railway MySQL, Aiven, AWS RDS and so on). Build the URL as `mysql+pymysql://USER:PASSWORD@HOST:PORT/DBNAME`.
2. **API:** root `backend`, build `pip install -r requirements.txt`, start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Set `DATABASE_URL`, `JWT_SECRET_KEY` and `CORS_ORIGINS` as environment variables in the platform dashboard instead of uploading a `.env` file.
3. **UI:** root `frontend`, build `npm install`, start `npm start`. Set `BACKEND_URL` to the API's public URL.

## How I used AI tools

> Edit this note so it is true for you before you submit.

I used an AI assistant to scaffold the FastAPI project, the tests and the Express proxy. I read through all of it, ran the tests, and changed: (1) ... (2) ... I rejected or modified: (1) ...