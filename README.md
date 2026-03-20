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

Authentication identities can also be bootstrapped for local development. `BOOTSTRAP_AUTH_USERS=true` seeds starter users into the database, but it is disabled by default so demo credentials are not published in the repo.

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

### Local Secrets Hygiene

- Keep real credentials in untracked `.env` files only.
- Install the local pre-commit guard with `powershell -ExecutionPolicy Bypass -File scripts/install_git_hooks.ps1`
- Run `python scripts/scan_secrets.py` any time you want a quick repo scan before pushing.

### Docker Desktop

```bash
cd infra/docker
docker compose up --build
```

If the backend keeps printing `Waiting for PostgreSQL...` and the Postgres logs say `Role "app_user" does not exist`, the named Docker volume was likely initialized earlier with different credentials. In local development, the simplest recovery is:

```bash
cd infra/docker
docker compose down
docker volume rm intelligence-os_torilaure-postgres-data
docker compose up --build
```

Only remove that volume if you are comfortable discarding the local Postgres data stored in the Docker stack.

Local defaults:
- Frontend: `http://localhost:5174`
- Backend: `http://localhost:8000`

Local login:
- Use `Create account` in the UI to register a local user.
- Enable `BOOTSTRAP_AUTH_USERS=true` only if you explicitly want seeded local test accounts.

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

## New ROI Recommendation + PDF Export Features

Implemented in recent dev work:

- Backend ROI pipeline includes:
  - `/projects/{id}/roi-scenarios/calculate` for scenario preview + analysis + recommendation
  - `/projects/{id}/roi-scenarios/analyze` for full risk/stress diagnostic output
  - `/projects/{id}/roi-scenarios/{scenario_id}/recommendations` (POST/GET) for persisted analyst recommendation audit
  - `/projects/{id}/roi-scenarios/{scenario_id}/recommendations/pdf` (GET) for downloadable PDF of recommendations
- Recommendation model persists `RoiScenarioRecommendation` with `RoiRecommendationSummary` fields:
  - `recommendation` (`invest/watch/reject`), `conviction`, `score`
  - `rationale`, `required_assumption_checks`, `action_items`
- Persistence in `platform_storage_service`, with new SQLAlchemy table `ProjectRoiScenarioRecommendationRecord` and Alembic migration
- PDF generator in `platform_service.get_project_roi_recommendations_pdf(...)` using ReportLab
- Frontend support in `frontend-app/src/api/projectClient.js` and `ProjectDetailPage.jsx` with create/list recommendation and download button
- Automated tests added in `platform-core/tests/test_project_roi_api.py` (including PDF endpoint)

### Dev workflow notes

- New dependency: `reportlab` in `platform-core/requirements.txt`
- Regression test command: `pytest -q` (now 13 passed)
- New migration script in `alembic/versions` to apply before startup

## Suggested Next Steps

1. Add external connectors for broker feeds, CRM exports, and market data providers.
2. Add Microsoft OAuth and enterprise identity federation.
3. Add deeper project workspaces with project detail, members, notes, and document uploads.
4. Move scoring, retrieval, and notifications to independent services behind an API gateway.
5. Add background workers and scheduling for unattended ingestion runs.
