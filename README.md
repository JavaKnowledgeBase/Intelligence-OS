# Torilaure Intelligence OS

Standalone foundation for an investment intelligence and ROI platform with a React frontend and Python backend.

Developer: Ravi Kafley

Security baseline:
- [SECURITY.md](c:\Users\rkafl\Documents\Projects\torilaure-roi\torilaure-intelligence-os\SECURITY.md)
- [docs/security-baseline.md](c:\Users\rkafl\Documents\Projects\torilaure-roi\torilaure-intelligence-os\docs\security-baseline.md)

## Repository Layout

```text
torilaure-intelligence-os/
  docs/
  platform-core/
  frontend-app/
  services/
    forecast-service/
    valuation-service/
  infra/
    docker/
```

## What Is Included

- `platform-core`: FastAPI application with shared project, listing, ROI, scoring, market, search, and alert APIs.
- `frontend-app`: React + Vite application with login, dashboard, architecture, about, and project workspace pages.
- `services/forecast-service`: starter Python service for retail demand forecasting.
- `services/valuation-service`: starter Python service for business and asset valuation.
- `infra/docker`: local Docker Compose stack for the API, web app, PostgreSQL, and Redis.

## Quick Start

### Backend

```bash
cd platform-core
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### Security Infrastructure

For persistent security state, start PostgreSQL and Redis first:

```bash
cd infra/docker
docker compose up -d postgres redis
```

If your local machine already uses port `5432` or `6379`, override `DATABASE_URL` and `REDIS_URL` using values based on [platform-core/.env.example](c:\Users\rkafl\Documents\Projects\torilaure-roi\torilaure-intelligence-os\platform-core\.env.example).

The platform domain now uses PostgreSQL as its primary source of truth for projects, listings, market insights, and alert rules. Sample data is no longer loaded by default. If you want a demo bootstrap on a fresh local database, set `BOOTSTRAP_SAMPLE_DATA=true` before starting the backend.

Authentication identities can also be bootstrapped for local development. `BOOTSTRAP_AUTH_USERS=true` seeds the starter users into the database, and their passwords remain stored as salted `scrypt` hashes rather than plaintext.

Refresh/session state is now designed for multi-instance deployments through Redis-backed session persistence. Refresh token rotation, logout invalidation, and active session checks are coordinated through Redis, with a local fallback used only if Redis is unavailable.

### Migrations

Run schema migrations before starting the backend:

```bash
cd platform-core
alembic upgrade head
```

Create a new migration after model changes:

```bash
cd platform-core
alembic revision --autogenerate -m "describe change"
```

### Ingestion Pipeline

The backend includes a local ingestion pipeline that upserts feed data into PostgreSQL-backed listings and market insights while writing ingestion run history.

- Feed files live in [platform-core/data_sources](c:\Users\rkafl\Documents\Projects\torilaure-roi\torilaure-intelligence-os\platform-core\data_sources)
- Trigger a sync with `POST /api/v1/ingestion/sync`
- Review run history with `GET /api/v1/ingestion/runs`

The starter local feed source is `starter_feed`.

### Frontend

Recommended runtime:
- Node.js `20.x` or `22.x` LTS

```bash
cd frontend-app
npm install
npm run dev
```

### Docker Desktop

```bash
cd infra/docker
docker compose up --build
```

Local defaults:
- Frontend: `http://localhost:5174`
- Backend: `http://localhost:8000`

Demo login:
- `ravi@torilaure.com`
- `Torilaure123!`

Implemented self-service auth:
- create account
- request admin access
- password reset test flow

## Current Product Surface

- `Login`: email/password sign-in, self-service account creation, admin-access request, password reset test flow
- `Dashboard`: live overview, featured deals, and market signals from FastAPI
- `Projects`: shared project workspace with project listing and guided project creation
- `Architecture`: system blueprint for the platform foundation
- `About`: in-app references to setup, security, architecture, and OAuth planning docs

## Suggested Next Steps

1. Add external connectors for broker feeds, CRM exports, and market data providers.
2. Add Microsoft OAuth and enterprise identity federation.
3. Add deeper project workspaces with project detail, members, notes, and document uploads.
4. Move scoring, retrieval, and notifications to independent services behind an API gateway.
5. Add background workers and scheduling for unattended ingestion runs.
