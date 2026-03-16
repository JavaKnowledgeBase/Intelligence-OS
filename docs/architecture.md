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

- React frontend for the investor dashboard and project workspace
- FastAPI platform core for project, listing, ROI, market, search, and alert flows
- placeholder microservices for forecast and valuation workloads
- Docker Compose for local development

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
