# Project Setup Reference

Developer: Ravi Kafley

This document captures the current Torilaure Intelligence OS scaffold so we can refresh setup context later without re-reading the whole codebase.

## Repository Structure Created

```text
torilaure-intelligence-os/
  docs/
  frontend-app/
  infra/docker/
  platform-core/
  services/
    forecast-service/
    valuation-service/
```

## Frontend Files Created

Core app shell:
- `frontend-app/src/main.jsx`
- `frontend-app/src/App.jsx`
- `frontend-app/src/styles/index.css`

Auth/session helpers:
- `frontend-app/src/auth.js`
- `frontend-app/src/api/authClient.js`
- `frontend-app/src/api/sessionClient.js`
- `frontend-app/src/api/projectClient.js`

Pages:
- `frontend-app/src/pages/LoginPage.jsx`
- `frontend-app/src/pages/DashboardPage.jsx`
- `frontend-app/src/pages/ArchitecturePage.jsx`
- `frontend-app/src/pages/AboutPage.jsx`
- `frontend-app/src/pages/ProjectsPage.jsx`

Components:
- `frontend-app/src/components/BrandMark.jsx`
- `frontend-app/src/components/ProtectedRoute.jsx`
- `frontend-app/src/components/SectionTitle.jsx`
- `frontend-app/src/components/WisdomTicker.jsx`

Static content:
- `frontend-app/src/data/dashboardData.js`
- `frontend-app/src/data/architectureData.js`
- `frontend-app/src/data/wisdomLines.js`

Frontend config/build:
- `frontend-app/package.json`
- `frontend-app/package-lock.json`
- `frontend-app/index.html`
- `frontend-app/vite.config.js`
- `frontend-app/Dockerfile`
- `frontend-app/nginx.conf`
- `frontend-app/.dockerignore`

## Backend Files Created

App entry and config:
- `platform-core/app/main.py`
- `platform-core/app/core/config.py`
- `platform-core/app/core/database.py`
- `platform-core/app/core/redis_client.py`

API layer:
- `platform-core/app/api/router.py`
- `platform-core/app/api/deps.py`
- `platform-core/app/api/routes/auth.py`
- `platform-core/app/api/routes/projects.py`
- `platform-core/app/api/routes/listings.py`
- `platform-core/app/api/routes/market.py`
- `platform-core/app/api/routes/alerts.py`
- `platform-core/app/api/routes/ingestion.py`

Schemas:
- `platform-core/app/schemas/auth.py`
- `platform-core/app/schemas/project.py`
- `platform-core/app/schemas/listing.py`
- `platform-core/app/schemas/market.py`
- `platform-core/app/schemas/alert.py`
- `platform-core/app/schemas/ingestion.py`

Persistence models:
- `platform-core/app/models/platform_tables.py`
- `platform-core/app/models/security_tables.py`
- `platform-core/app/models/auth_seed.py`
- `platform-core/app/models/seed_data.py`

Services:
- `platform-core/app/services/auth_service.py`
- `platform-core/app/services/authorization_service.py`
- `platform-core/app/services/platform_service.py`
- `platform-core/app/services/platform_storage_service.py`
- `platform-core/app/services/security_storage_service.py`
- `platform-core/app/services/user_storage_service.py`
- `platform-core/app/services/session_store_service.py`
- `platform-core/app/services/revoked_token_service.py`
- `platform-core/app/services/rate_limit_service.py`
- `platform-core/app/services/audit_service.py`
- `platform-core/app/services/ingestion_service.py`

Database/migrations:
- `platform-core/alembic.ini`
- `platform-core/alembic/env.py`
- `platform-core/alembic/script.py.mako`
- `platform-core/alembic/versions/20260316_000001_initial_schema.py`
- `platform-core/alembic/versions/20260316_000002_session_and_ingestion.py`
- `platform-core/alembic/versions/20260316_000003_auth_self_service.py`

Data sources:
- `platform-core/data_sources/starter_feed.json`

Backend config:
- `platform-core/requirements.txt`
- `platform-core/.env.example`
- `platform-core/Dockerfile`
- `platform-core/.dockerignore`

## Supporting Files Created

- `README.md`
- `SECURITY.md`
- `docs/architecture.md`
- `docs/security-baseline.md`
- `infra/docker/docker-compose.yml`
- `services/forecast-service/app/main.py`
- `services/forecast-service/requirements.txt`
- `services/valuation-service/app/main.py`
- `services/valuation-service/requirements.txt`

## Frameworks And Libraries Imported

Frontend:
- `react`
- `react-dom`
- `react-router-dom`
- `vite`
- `@vitejs/plugin-react`
- `nginx` in the production container image

Backend:
- `fastapi`
- `uvicorn`
- `pydantic`
- `email-validator`
- `PyJWT`
- `SQLAlchemy`
- `psycopg[binary]`
- `redis`
- `alembic`
- `python-multipart` if form uploads are added later

Python standard library used in the backend:
- `os`
- `logging`
- `json`
- `hashlib`
- `hmac`
- `statistics`
- `pathlib`
- `contextlib`
- `collections`
- `datetime`
- `uuid`
- `typing`

## Current Import Inventory

Frontend imports in use:
- React primitives: `useEffect`, `useMemo`, `useState`
- Router primitives: `BrowserRouter`, `NavLink`, `Navigate`, `Route`, `Routes`, `useLocation`, `useNavigate`
- Local modules:
  - auth/session helpers from `./auth` and `./api/*`
  - page components from `./pages/*`
  - reusable components from `./components/*`
  - data modules from `./data/*`
  - global stylesheet from `./styles/index.css`

Backend imports in use:
- FastAPI runtime: `FastAPI`, `APIRouter`, `Depends`, `Header`, `HTTPException`, `Query`, `Request`, `Response`, `status`
- FastAPI middleware/response helpers: `CORSMiddleware`, `Response`
- Pydantic models/types: `BaseModel`, `Field`, `EmailStr`
- SQLAlchemy core/ORM: `create_engine`, `select`, `inspect`, `DeclarativeBase`, `sessionmaker`, `Mapped`, `mapped_column`, `relationship`
- Redis client: `Redis`, `RedisError`
- JWT handling: `jwt`
- Local backend modules:
  - `app.api.*`
  - `app.core.*`
  - `app.models.*`
  - `app.schemas.*`
  - `app.services.*`

## Current Runtime Building Blocks

Frontend:
- React + Vite SPA
- React Router page routing
- localStorage-backed frontend session state
- FastAPI API consumption through `fetch`
- Dockerized static frontend served by `nginx`

Backend:
- FastAPI app with versioned `/api/v1` routes
- PostgreSQL-backed domain and auth persistence
- Redis-backed rate limiting and session persistence with fallback
- JWT auth with refresh rotation and logout invalidation
- Alembic-managed schema migrations
- local file-based ingestion pipeline
- Dockerized API startup with migration-first boot

## Notes For Future Resume

- Frontend default local port: `5174`
- Backend default local port: `8000`
- Run backend migrations before startup: `alembic upgrade head`
- Sample domain data is optional: `BOOTSTRAP_SAMPLE_DATA=true`
- Sample auth users are optional: `BOOTSTRAP_AUTH_USERS=true`
