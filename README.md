# Barber Platform

Telegram Mini App platform for independent barbers operating at a shared physical location. The current prototype supports one location and approximately ten independent barbers while preserving a path to future multi-location SaaS.

## Current status: Stage 3

Implemented capabilities:

- Secure barber and customer authentication through Telegram Mini App `initData` verification.
- Barber profile, services, weekly schedule, and blocked/personal time.
- Customer booking wizard: location, barber (or any available), multi-service, date, and 15-minute slots.
- Availability engine using working schedule, blocked time, active appointments, and service duration.
- Atomic booking with historical price/duration snapshots and race-condition protection.
- Customer appointment list and cancellation (1-hour cutoff).
- Barber appointment list, cancellation, and walk-in creation.

Not in this stage: complete/no-show workflows, finance, notifications, and SaaS administration.

## Technology

- Python 3.12, FastAPI, SQLAlchemy 2 async, Alembic, PostgreSQL
- Aiogram 3 (reserved for future bot integration)
- React, Vite, TypeScript, Telegram Mini App SDK

Docker is intentionally not used by this project.

## Local setup

### 1. PostgreSQL

Run PostgreSQL locally and create separate development and test databases. The test database is mandatory for pytest and must not be the development database.

```sql
CREATE DATABASE barber_db;
CREATE DATABASE barber_test_db;
```

### 2. Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env: configure PostgreSQL and a newly rotated Telegram bot token.
alembic upgrade head
uvicorn app.main:app --reload
```

The API is available at `http://localhost:8000`; development API documentation is available at `/docs`.

### 3. Frontend

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

The development frontend is available at `http://localhost:5173`.

## Environment configuration

Backend configuration is loaded from `backend/.env`. It must never be committed.

| Variable | Purpose |
| --- | --- |
| `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | Development database connection |
| `TEST_POSTGRES_DB` | Dedicated destructive-test database, default `barber_test_db` |
| `TELEGRAM_BOT_TOKEN` | Active token from BotFather; required for production Telegram authentication |
| `TELEGRAM_WEBHOOK_SECRET` | Reserved webhook secret |
| `TELEGRAM_INIT_DATA_MAX_AGE_SECONDS` | Accepted `initData` age; default 3600 seconds |
| `TELEGRAM_INIT_DATA_FUTURE_SKEW_SECONDS` | Allowed future clock skew; default 30 seconds |
| `CORS_ORIGINS` | JSON list of allowed frontend origins |

Rotate a token in BotFather before placing it in `.env`; never copy tokens into source code or documentation.

## Migrations

```powershell
cd backend
.venv\Scripts\activate
alembic upgrade head
alembic current
```

Migrations are applied to the development database configured by `POSTGRES_DB`. Never run them against the test database as a substitute for application migrations.

## Tests

```powershell
cd backend
.venv\Scripts\activate
pytest
```

Pytest uses `TEST_POSTGRES_DB`, creates its tables there, and drops them at teardown. The test configuration rejects a test database that matches `POSTGRES_DB` or is not clearly named with a `_test`/`_test_db` suffix.

## Telegram authentication

The frontend forwards the query string supplied by `Telegram.WebApp.initData` in the `Authorization: tma <initData>` header. The backend verifies Telegram's HMAC signature, requires a valid `auth_date`, rejects stale or implausibly future data, and obtains the authenticated barber from the verified Telegram user ID. Client-supplied barber IDs are never used for ownership.
