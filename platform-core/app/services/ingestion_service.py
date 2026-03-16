from __future__ import annotations

import json
from pathlib import Path

from app.schemas.auth import AuthUser
from app.schemas.ingestion import IngestionRunSummary
from app.schemas.listing import ListingSummary
from app.schemas.market import MarketInsight
from app.services.authorization_service import authorization_service
from app.services.platform_storage_service import platform_storage_service


class IngestionService:
    """Local ingestion pipeline that syncs source files into PostgreSQL-backed domain tables."""

    def __init__(self) -> None:
        self._data_dir = Path(__file__).resolve().parents[2] / "data_sources"

    def list_runs(self, user: AuthUser) -> list[IngestionRunSummary]:
        authorization_service.require_tenant_editor(user)
        return platform_storage_service.list_ingestion_runs(user.tenant_id)

    def sync_source(self, source_name: str, user: AuthUser) -> IngestionRunSummary:
        authorization_service.require_tenant_editor(user)
        if not platform_storage_service.is_available():
            raise RuntimeError("Platform storage is unavailable. Run migrations and connect PostgreSQL first.")

        feed = self._load_feed(source_name=source_name, tenant_id=user.tenant_id)
        run = platform_storage_service.create_ingestion_run(
            tenant_id=user.tenant_id,
            source_name=source_name,
            status="running",
            detail="Sync started.",
        )

        created = 0
        updated = 0
        processed = 0

        for listing_data in feed.get("listings", []):
            listing = ListingSummary(**listing_data)
            _, action = platform_storage_service.upsert_listing(
                tenant_id=user.tenant_id,
                source_name=source_name,
                payload=listing,
            )
            created += 1 if action == "created" else 0
            updated += 1 if action == "updated" else 0
            processed += 1

        for insight_data in feed.get("market_insights", []):
            insight = MarketInsight(**insight_data)
            _, action = platform_storage_service.upsert_market_insight(
                tenant_id=user.tenant_id,
                source_name=source_name,
                payload=insight,
            )
            created += 1 if action == "created" else 0
            updated += 1 if action == "updated" else 0
            processed += 1

        return platform_storage_service.complete_ingestion_run(
            run_id=run.id,
            status="completed",
            detail=f"Synced {processed} records from {source_name}.",
            records_processed=processed,
            records_created=created,
            records_updated=updated,
        ) or run

    def _load_feed(self, *, source_name: str, tenant_id: str) -> dict:
        file_path = self._data_dir / f"{source_name.replace('-', '_')}.json"
        if not file_path.exists():
            raise FileNotFoundError(f"Feed source '{source_name}' was not found.")
        payload = json.loads(file_path.read_text(encoding="utf-8"))
        if payload.get("tenant_id") not in {None, tenant_id}:
            raise PermissionError("Feed source tenant does not match the current user tenant.")
        return payload


ingestion_service = IngestionService()
