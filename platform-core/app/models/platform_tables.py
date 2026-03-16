from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


# Developer: Ravi Kafley
class ProjectRecord(Base):
    """Persistent project table scoped by tenant and enriched with membership rows."""

    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    project_type: Mapped[str] = mapped_column(String(120), nullable=False)
    owner: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    active_deals: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stage: Mapped[str] = mapped_column(String(40), nullable=False, default="screening")
    investment_thesis: Mapped[str] = mapped_column(Text, nullable=False, default="")
    target_irr: Mapped[float | None] = mapped_column(Float, nullable=True)
    budget_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    members: Mapped[list["ProjectMemberRecord"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class ProjectMemberRecord(Base):
    """Join table that captures which users can directly access a project."""

    __tablename__ = "project_members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    project: Mapped[ProjectRecord] = relationship(back_populates="members")


class ListingRecord(Base):
    """Persistent opportunity catalog for tenant-scoped listing access."""

    __tablename__ = "listings"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_name: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    project_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("projects.id"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    asset_class: Mapped[str] = mapped_column(String(80), nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    asking_price: Mapped[float] = mapped_column(Float, nullable=False)
    projected_irr: Mapped[float] = mapped_column(Float, nullable=False)
    deal_score: Mapped[int] = mapped_column(Integer, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(40), nullable=False, default="medium")
    occupancy_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    hold_period_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="pipeline")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class MarketInsightRecord(Base):
    """Persistent market signals that remain isolated by tenant."""

    __tablename__ = "market_insights"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_name: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    region: Mapped[str] = mapped_column(String(120), nullable=False)
    signal: Mapped[str] = mapped_column(Text, nullable=False)
    trend: Mapped[str] = mapped_column(String(40), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String(120), nullable=False, default="internal-research")
    as_of_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class AlertPreferenceRecord(Base):
    """Persistent alert rules used by the dashboard notification center."""

    __tablename__ = "alert_preferences"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    channel: Mapped[str] = mapped_column(String(80), nullable=False)
    trigger: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    scope: Mapped[str] = mapped_column(String(80), nullable=False, default="tenant")
    severity: Mapped[str] = mapped_column(String(40), nullable=False, default="medium")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class UserRecord(Base):
    """Persistent user identity table storing hashed passwords and tenant membership."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class IngestionRunRecord(Base):
    """Persistent log of data ingestion runs for operational visibility and auditability."""

    __tablename__ = "ingestion_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    records_processed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_updated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    detail: Mapped[str] = mapped_column(Text, nullable=False, default="")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AccessRequestRecord(Base):
    """Persistent request for elevated access submitted from the login page."""

    __tablename__ = "access_requests"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    requested_role: Mapped[str] = mapped_column(String(64), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class PasswordResetRecord(Base):
    """One-time password reset token persisted for starter self-service recovery."""

    __tablename__ = "password_reset_requests"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    reset_token: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
