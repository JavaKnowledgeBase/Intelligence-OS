from __future__ import annotations

import logging
from contextlib import contextmanager, suppress
from datetime import UTC, date, datetime
from uuid import uuid4

from sqlalchemy import inspect, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload

from app.core.database import SessionLocal, engine
from app.core.config import settings
from app.models.platform_tables import (
    AlertPreferenceRecord,
    IngestionRunRecord,
    ListingRecord,
    MarketInsightRecord,
    ProjectDocumentRecord,
    ProjectMemberRecord,
    ProjectNoteRecord,
    ProjectRecord,
)
from app.models.seed_data import ALERTS, LISTINGS, MARKET_INSIGHTS, PROJECTS
from app.schemas.alert import AlertPreference, AlertPreferenceCreate
from app.schemas.document import ProjectDocumentSummary
from app.schemas.ingestion import IngestionRunSummary
from app.schemas.listing import ListingCreate, ListingSummary
from app.schemas.market import MarketInsight, MarketInsightCreate
from app.schemas.note import ProjectNoteSummary
from app.schemas.project import ProjectSummary


logger = logging.getLogger("torilaure.platform.persistence")


# Developer: Ravi Kafley
class PlatformStorageService:
    """Persistent storage facade for tenant-scoped platform resources."""

    def __init__(self) -> None:
        self._available = False

    def initialize(self) -> None:
        try:
            inspector = inspect(engine)
            required_tables = {
                "projects",
                "project_members",
                "listings",
                "market_insights",
                "alert_preferences",
                "ingestion_runs",
                "project_documents",
                "project_notes",
            }
            if not required_tables.issubset(set(inspector.get_table_names())):
                raise SQLAlchemyError("Platform tables are missing. Run `alembic upgrade head`.")
            if settings.bootstrap_sample_data:
                with self.session_scope() as session:
                    self._seed_if_empty(session)
            self._available = True
        except SQLAlchemyError as error:
            self._available = False
            logger.warning("Platform storage initialization fell back to in-memory mode: %s", error)

    def is_available(self) -> bool:
        return self._available

    @contextmanager
    def session_scope(self):
        session = SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            with suppress(Exception):
                session.rollback()
            raise
        finally:
            session.close()

    def list_projects(self) -> list[ProjectSummary]:
        with self.session_scope() as session:
            records = session.scalars(
                select(ProjectRecord)
                .options(selectinload(ProjectRecord.members))
                .order_by(ProjectRecord.name.asc())
            ).all()
            return [self._to_project_summary(record) for record in records]

    def get_project(self, project_id: str) -> ProjectSummary | None:
        with self.session_scope() as session:
            record = session.scalar(
                select(ProjectRecord)
                .options(selectinload(ProjectRecord.members))
                .where(ProjectRecord.id == project_id)
            )
            if record is None:
                return None
            return self._to_project_summary(record)

    def create_project(self, project: ProjectSummary) -> ProjectSummary:
        with self.session_scope() as session:
            record = ProjectRecord(
                id=project.id,
                name=project.name,
                tenant_id=project.tenant_id,
                project_type=project.project_type,
                owner=project.owner,
                owner_id=project.owner_id,
                status=project.status,
                active_deals=project.active_deals,
                stage=project.stage,
                investment_thesis=project.investment_thesis,
                target_irr=project.target_irr,
                budget_amount=project.budget_amount,
                members=[ProjectMemberRecord(user_id=user_id) for user_id in project.member_ids],
            )
            session.add(record)
            session.flush()
            session.refresh(record)
            return self._to_project_summary(record)

    def list_project_documents(self, tenant_id: str, project_id: str) -> list[ProjectDocumentSummary]:
        with self.session_scope() as session:
            records = session.scalars(
                select(ProjectDocumentRecord)
                .where(
                    ProjectDocumentRecord.tenant_id == tenant_id,
                    ProjectDocumentRecord.project_id == project_id,
                )
                .order_by(ProjectDocumentRecord.uploaded_at.desc(), ProjectDocumentRecord.file_name.asc())
            ).all()
            return [self._to_project_document_summary(record) for record in records]

    def create_project_document(
        self,
        *,
        project_id: str,
        tenant_id: str,
        file_name: str,
        stored_name: str,
        content_type: str,
        file_size_bytes: int,
        uploaded_by: str,
        processing_status: str,
        preview_available: bool,
        extracted_text_excerpt: str,
    ) -> ProjectDocumentSummary:
        with self.session_scope() as session:
            record = ProjectDocumentRecord(
                id=f"doc-{uuid4().hex[:8]}",
                project_id=project_id,
                tenant_id=tenant_id,
                file_name=file_name,
                stored_name=stored_name,
                content_type=content_type,
                file_size_bytes=file_size_bytes,
                uploaded_by=uploaded_by,
                processing_status=processing_status,
                preview_available=preview_available,
                extracted_text_excerpt=extracted_text_excerpt,
            )
            session.add(record)
            session.flush()
            session.refresh(record)
            return self._to_project_document_summary(record)

    def list_project_notes(self, tenant_id: str, project_id: str) -> list[ProjectNoteSummary]:
        with self.session_scope() as session:
            records = session.scalars(
                select(ProjectNoteRecord)
                .where(
                    ProjectNoteRecord.tenant_id == tenant_id,
                    ProjectNoteRecord.project_id == project_id,
                )
                .order_by(ProjectNoteRecord.created_at.desc())
            ).all()
            return [self._to_project_note_summary(record) for record in records]

    def create_project_note(
        self,
        *,
        project_id: str,
        tenant_id: str,
        author_name: str,
        content: str,
    ) -> ProjectNoteSummary:
        with self.session_scope() as session:
            record = ProjectNoteRecord(
                id=f"note-{uuid4().hex[:8]}",
                project_id=project_id,
                tenant_id=tenant_id,
                author_name=author_name,
                content=content,
            )
            session.add(record)
            session.flush()
            session.refresh(record)
            return self._to_project_note_summary(record)

    def list_listings(self, tenant_id: str) -> list[ListingSummary]:
        with self.session_scope() as session:
            records = session.scalars(
                select(ListingRecord)
                .where(ListingRecord.tenant_id == tenant_id)
                .order_by(ListingRecord.deal_score.desc(), ListingRecord.title.asc())
            ).all()
            return [self._to_listing_summary(record) for record in records]

    def create_listing(self, tenant_id: str, payload: ListingCreate) -> ListingSummary:
        with self.session_scope() as session:
            record = ListingRecord(
                id=f"deal-{uuid4().hex[:8]}",
                tenant_id=tenant_id,
                source_name=None,
                project_id=payload.project_id,
                title=payload.title,
                asset_class=payload.asset_class,
                location=payload.location,
                asking_price=payload.asking_price,
                projected_irr=payload.projected_irr,
                deal_score=payload.deal_score,
                summary=payload.summary,
                risk_level=payload.risk_level,
                occupancy_rate=payload.occupancy_rate,
                hold_period_months=payload.hold_period_months,
                status=payload.status,
            )
            session.add(record)
            session.flush()
            session.refresh(record)
            return self._to_listing_summary(record)

    def upsert_listing(self, *, tenant_id: str, source_name: str, payload: ListingSummary) -> tuple[ListingSummary, str]:
        with self.session_scope() as session:
            record = session.get(ListingRecord, payload.id)
            action = "updated" if record is not None else "created"
            if record is None:
                record = ListingRecord(id=payload.id, tenant_id=tenant_id)
                session.add(record)
            record.tenant_id = tenant_id
            record.source_name = source_name
            record.project_id = payload.project_id
            record.title = payload.title
            record.asset_class = payload.asset_class
            record.location = payload.location
            record.asking_price = payload.asking_price
            record.projected_irr = payload.projected_irr
            record.deal_score = payload.deal_score
            record.summary = payload.summary
            record.risk_level = payload.risk_level
            record.occupancy_rate = payload.occupancy_rate
            record.hold_period_months = payload.hold_period_months
            record.status = payload.status
            session.flush()
            session.refresh(record)
            return self._to_listing_summary(record), action

    def list_market_insights(self, tenant_id: str) -> list[MarketInsight]:
        with self.session_scope() as session:
            records = session.scalars(
                select(MarketInsightRecord)
                .where(MarketInsightRecord.tenant_id == tenant_id)
                .order_by(MarketInsightRecord.region.asc())
            ).all()
            return [self._to_market_insight(record) for record in records]

    def create_market_insight(self, tenant_id: str, payload: MarketInsightCreate) -> MarketInsight:
        with self.session_scope() as session:
            record = MarketInsightRecord(
                id=f"insight-{uuid4().hex[:8]}",
                tenant_id=tenant_id,
                source_name=payload.source,
                region=payload.region,
                signal=payload.signal,
                trend=payload.trend,
                confidence=payload.confidence,
                source=payload.source,
                as_of_date=payload.as_of_date,
            )
            session.add(record)
            session.flush()
            session.refresh(record)
            return self._to_market_insight(record)

    def upsert_market_insight(
        self,
        *,
        tenant_id: str,
        source_name: str,
        payload: MarketInsight,
    ) -> tuple[MarketInsight, str]:
        with self.session_scope() as session:
            record = session.get(MarketInsightRecord, payload.id)
            action = "updated" if record is not None else "created"
            if record is None:
                record = MarketInsightRecord(id=payload.id, tenant_id=tenant_id)
                session.add(record)
            record.tenant_id = tenant_id
            record.source_name = source_name
            record.region = payload.region
            record.signal = payload.signal
            record.trend = payload.trend
            record.confidence = payload.confidence
            record.source = payload.source
            record.as_of_date = payload.as_of_date
            session.flush()
            session.refresh(record)
            return self._to_market_insight(record), action

    def list_alerts(self, tenant_id: str) -> list[AlertPreference]:
        with self.session_scope() as session:
            records = session.scalars(
                select(AlertPreferenceRecord)
                .where(AlertPreferenceRecord.tenant_id == tenant_id)
                .order_by(AlertPreferenceRecord.name.asc())
            ).all()
            return [self._to_alert_preference(record) for record in records]

    def create_alert(self, tenant_id: str, payload: AlertPreferenceCreate) -> AlertPreference:
        with self.session_scope() as session:
            record = AlertPreferenceRecord(
                id=f"alert-{uuid4().hex[:8]}",
                tenant_id=tenant_id,
                name=payload.name,
                channel=payload.channel,
                trigger=payload.trigger,
                enabled=payload.enabled,
                scope=payload.scope,
                severity=payload.severity,
            )
            session.add(record)
            session.flush()
            session.refresh(record)
            return self._to_alert_preference(record)

    def create_ingestion_run(
        self,
        *,
        tenant_id: str,
        source_name: str,
        status: str,
        detail: str,
    ) -> IngestionRunSummary:
        with self.session_scope() as session:
            record = IngestionRunRecord(
                id=f"ingest-{uuid4().hex[:8]}",
                tenant_id=tenant_id,
                source_name=source_name,
                status=status,
                detail=detail,
                records_processed=0,
                records_created=0,
                records_updated=0,
            )
            session.add(record)
            session.flush()
            session.refresh(record)
            return self._to_ingestion_run_summary(record)

    def complete_ingestion_run(
        self,
        *,
        run_id: str,
        status: str,
        detail: str,
        records_processed: int,
        records_created: int,
        records_updated: int,
    ) -> IngestionRunSummary | None:
        with self.session_scope() as session:
            record = session.get(IngestionRunRecord, run_id)
            if record is None:
                return None
            record.status = status
            record.detail = detail
            record.records_processed = records_processed
            record.records_created = records_created
            record.records_updated = records_updated
            record.completed_at = datetime.now(UTC)
            session.flush()
            session.refresh(record)
            return self._to_ingestion_run_summary(record)

    def list_ingestion_runs(self, tenant_id: str) -> list[IngestionRunSummary]:
        with self.session_scope() as session:
            records = session.scalars(
                select(IngestionRunRecord)
                .where(IngestionRunRecord.tenant_id == tenant_id)
                .order_by(IngestionRunRecord.started_at.desc())
            ).all()
            return [self._to_ingestion_run_summary(record) for record in records]

    def _seed_if_empty(self, session) -> None:
        if session.scalar(select(ProjectRecord.id).limit(1)) is None:
            for item in PROJECTS:
                session.add(
                    ProjectRecord(
                        id=item["id"],
                        name=item["name"],
                        tenant_id=item["tenant_id"],
                        project_type=item["project_type"],
                        owner=item["owner"],
                        owner_id=item["owner_id"],
                        status=item["status"],
                        active_deals=item["active_deals"],
                        stage=item.get("stage", "screening"),
                        investment_thesis=item.get("investment_thesis", ""),
                        target_irr=item.get("target_irr"),
                        budget_amount=item.get("budget_amount"),
                        members=[ProjectMemberRecord(user_id=user_id) for user_id in item["member_ids"]],
                    )
                )
            # Flush projects before dependent listings so FK-backed seeds load correctly.
            session.flush()
        if session.scalar(select(ListingRecord.id).limit(1)) is None:
            for item in LISTINGS:
                session.add(ListingRecord(**item))
        if session.scalar(select(MarketInsightRecord.id).limit(1)) is None:
            for item in MARKET_INSIGHTS:
                session.add(
                    MarketInsightRecord(
                        **{
                            **item,
                            "as_of_date": date.fromisoformat(item["as_of_date"]) if item.get("as_of_date") else None,
                        }
                    )
                )
        if session.scalar(select(AlertPreferenceRecord.id).limit(1)) is None:
            for item in ALERTS:
                session.add(AlertPreferenceRecord(**item))

    def _to_project_summary(self, record: ProjectRecord) -> ProjectSummary:
        return ProjectSummary(
            id=record.id,
            name=record.name,
            tenant_id=record.tenant_id,
            project_type=record.project_type,
            owner=record.owner,
            owner_id=record.owner_id,
            member_ids=[member.user_id for member in record.members],
            status=record.status,
            active_deals=record.active_deals,
            stage=record.stage,
            investment_thesis=record.investment_thesis,
            target_irr=record.target_irr,
            budget_amount=record.budget_amount,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    def _to_listing_summary(self, record: ListingRecord) -> ListingSummary:
        return ListingSummary(
            id=record.id,
            project_id=record.project_id,
            title=record.title,
            asset_class=record.asset_class,
            location=record.location,
            asking_price=record.asking_price,
            projected_irr=record.projected_irr,
            deal_score=record.deal_score,
            summary=record.summary,
            risk_level=record.risk_level,
            occupancy_rate=record.occupancy_rate,
            hold_period_months=record.hold_period_months,
            status=record.status,
        )

    def _to_market_insight(self, record: MarketInsightRecord) -> MarketInsight:
        return MarketInsight(
            id=record.id,
            region=record.region,
            signal=record.signal,
            trend=record.trend,
            confidence=record.confidence,
            source=record.source,
            as_of_date=record.as_of_date,
        )

    def _to_alert_preference(self, record: AlertPreferenceRecord) -> AlertPreference:
        return AlertPreference(
            id=record.id,
            name=record.name,
            channel=record.channel,
            trigger=record.trigger,
            enabled=record.enabled,
            scope=record.scope,
            severity=record.severity,
        )

    def _to_ingestion_run_summary(self, record: IngestionRunRecord) -> IngestionRunSummary:
        return IngestionRunSummary(
            id=record.id,
            tenant_id=record.tenant_id,
            source_name=record.source_name,
            status=record.status,
            records_processed=record.records_processed,
            records_created=record.records_created,
            records_updated=record.records_updated,
            detail=record.detail,
            started_at=record.started_at,
            completed_at=record.completed_at,
        )

    def _to_project_document_summary(self, record: ProjectDocumentRecord) -> ProjectDocumentSummary:
        return ProjectDocumentSummary(
            id=record.id,
            project_id=record.project_id,
            tenant_id=record.tenant_id,
            file_name=record.file_name,
            stored_name=record.stored_name,
            content_type=record.content_type,
            file_size_bytes=record.file_size_bytes,
            uploaded_by=record.uploaded_by,
            processing_status=record.processing_status,
            preview_available=record.preview_available,
            extracted_text_excerpt=record.extracted_text_excerpt,
            uploaded_at=record.uploaded_at,
        )

    def _to_project_note_summary(self, record: ProjectNoteRecord) -> ProjectNoteSummary:
        return ProjectNoteSummary(
            id=record.id,
            project_id=record.project_id,
            tenant_id=record.tenant_id,
            author_name=record.author_name,
            content=record.content,
            created_at=record.created_at,
        )


platform_storage_service = PlatformStorageService()
