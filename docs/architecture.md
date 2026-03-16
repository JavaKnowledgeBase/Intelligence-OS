# Architecture Snapshot

Developer: Ravi Kafley

This scaffold follows the investment intelligence system design in the planning documents.

## Product Goal

Build one shared platform that can support:

- investment opportunity aggregation
- automated ROI analytics
- AI-powered deal ranking
- market intelligence dashboards
- alerts, search, and natural-language analysis

## Current Foundation

- React frontend for login, dashboard, architecture, about, and project workspace flows
- FastAPI platform core for auth, project, listing, ROI, market, search, alert, and ingestion flows
- placeholder microservices for forecast and valuation workloads
- PostgreSQL-backed domain/auth storage with Alembic migrations
- Redis-backed session persistence and rate limiting
- Docker Compose for local development and Docker Desktop verification

## Target Service Map

- API gateway and auth boundary
- deal service
- ROI service
- AI scoring service
- market intelligence service
- search and retrieval service
- notification service
- worker services for ingestion and processing

## Data Targets

- PostgreSQL for transactional data
- Redis for cache and background coordination
- object storage for files and extracted data
- vector database for RAG retrieval
- analytics warehouse for long-term reporting

## Current Gaps To Build Next

- project detail workspaces with documents, membership, and notes
- external ingestion connectors beyond the local starter feed
- Microsoft OAuth for enterprise identity federation
- asynchronous workers for scheduled sync, scoring, and alert delivery
