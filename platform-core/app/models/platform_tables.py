from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, func
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


class ProjectDocumentRecord(Base):
    """Metadata for project-scoped documents stored on local disk for now."""

    __tablename__ = "project_documents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    content_type: Mapped[str] = mapped_column(String(255), nullable=False, default="application/octet-stream")
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    uploaded_by: Mapped[str] = mapped_column(String(255), nullable=False)
    processing_status: Mapped[str] = mapped_column(String(40), nullable=False, default="ready")
    preview_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    extracted_text_excerpt: Mapped[str] = mapped_column(Text, nullable=False, default="")
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ProjectNoteRecord(Base):
    """Tenant-scoped notes that capture project decisions and collaboration context."""

    __tablename__ = "project_notes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    author_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    author_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ProjectRoiScenarioRecord(Base):
    """Saved project or listing ROI scenario assumptions with calculated outputs."""

    __tablename__ = "project_roi_scenarios"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    listing_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("listings.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    scenario_type: Mapped[str] = mapped_column(String(20), nullable=False, default="custom")
    lease_assumptions: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    purchase_price: Mapped[float] = mapped_column(Float, nullable=False)
    upfront_capex: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    annual_revenue: Mapped[float] = mapped_column(Float, nullable=False)
    vacancy_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    annual_operating_expenses: Mapped[float] = mapped_column(Float, nullable=False)
    annual_capex_reserve: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    initial_working_capital: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    working_capital_percent_of_revenue: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    annual_depreciation: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    acquisition_fee_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    loan_origination_fee_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    annual_revenue_growth_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    annual_expense_growth_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    exit_cap_rate: Mapped[float] = mapped_column(Float, nullable=False)
    exit_cost_rate: Mapped[float] = mapped_column(Float, nullable=False, default=2)
    hold_period_years: Mapped[int] = mapped_column(Integer, nullable=False)
    discount_rate: Mapped[float] = mapped_column(Float, nullable=False, default=12)
    risk_free_rate: Mapped[float] = mapped_column(Float, nullable=False, default=4.25)
    equity_risk_premium: Mapped[float] = mapped_column(Float, nullable=False, default=5.5)
    beta: Mapped[float] = mapped_column(Float, nullable=False, default=1.1)
    debt_spread: Mapped[float] = mapped_column(Float, nullable=False, default=2.0)
    tax_rate: Mapped[float] = mapped_column(Float, nullable=False, default=25.0)
    leverage_ratio: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    interest_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    interest_only_years: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    amortization_period_years: Mapped[int | None] = mapped_column(Integer, nullable=True)
    net_operating_income: Mapped[float] = mapped_column(Float, nullable=False)
    terminal_value: Mapped[float] = mapped_column(Float, nullable=False)
    total_profit: Mapped[float] = mapped_column(Float, nullable=False)
    equity_invested: Mapped[float] = mapped_column(Float, nullable=False)
    debt_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    ending_loan_balance: Mapped[float | None] = mapped_column(Float, nullable=True)
    sale_proceeds_after_debt: Mapped[float | None] = mapped_column(Float, nullable=True)
    average_annual_cash_flow: Mapped[float] = mapped_column(Float, nullable=False)
    projected_irr: Mapped[float | None] = mapped_column(Float, nullable=True)
    projected_npv: Mapped[float] = mapped_column(Float, nullable=False)
    cost_of_equity: Mapped[float | None] = mapped_column(Float, nullable=True)
    pre_tax_cost_of_debt: Mapped[float | None] = mapped_column(Float, nullable=True)
    after_tax_cost_of_debt: Mapped[float | None] = mapped_column(Float, nullable=True)
    weighted_average_cost_of_capital: Mapped[float | None] = mapped_column(Float, nullable=True)
    unlevered_irr: Mapped[float | None] = mapped_column(Float, nullable=True)
    unlevered_npv: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_tax_shield: Mapped[float | None] = mapped_column(Float, nullable=True)
    average_working_capital_balance: Mapped[float | None] = mapped_column(Float, nullable=True)
    cash_on_cash_multiple: Mapped[float] = mapped_column(Float, nullable=False)
    equity_multiple: Mapped[float | None] = mapped_column(Float, nullable=True)
    unlevered_equity_multiple: Mapped[float | None] = mapped_column(Float, nullable=True)
    average_annual_fcff: Mapped[float | None] = mapped_column(Float, nullable=True)
    average_annual_fcfe: Mapped[float | None] = mapped_column(Float, nullable=True)
    average_cash_on_cash_return: Mapped[float | None] = mapped_column(Float, nullable=True)
    first_year_cash_on_cash_return: Mapped[float | None] = mapped_column(Float, nullable=True)
    cap_rate_on_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    average_dscr: Mapped[float | None] = mapped_column(Float, nullable=True)
    minimum_dscr: Mapped[float | None] = mapped_column(Float, nullable=True)
    payback_period_years: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class ProjectRoiScenarioRecommendationRecord(Base):
    """Saved analyst recommendation with action and audit metadata."""

    __tablename__ = "project_roi_scenario_recommendations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scenario_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("project_roi_scenarios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_by: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    recommendation: Mapped[dict] = mapped_column(JSON, nullable=False)


class ProjectRoiActualRecord(Base):
    """Persisted realized operating results used for variance analysis against an ROI scenario."""

    __tablename__ = "project_roi_actuals"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scenario_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("project_roi_scenarios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    effective_revenue: Mapped[float] = mapped_column(Float, nullable=False)
    operating_expenses: Mapped[float] = mapped_column(Float, nullable=False)
    capex: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    debt_service: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    occupancy_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class BenchmarkCompRecord(Base):
    """Tenant-scoped comparable record used to calibrate benchmark ranges."""

    __tablename__ = "benchmark_comps"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    asset_class: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    location: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source_name: Mapped[str] = mapped_column(String(120), nullable=False)
    closed_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    sale_price: Mapped[float] = mapped_column(Float, nullable=False)
    net_operating_income: Mapped[float | None] = mapped_column(Float, nullable=True)
    cap_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    projected_irr: Mapped[float | None] = mapped_column(Float, nullable=True)
    equity_multiple: Mapped[float | None] = mapped_column(Float, nullable=True)
    average_dscr: Mapped[float | None] = mapped_column(Float, nullable=True)
    occupancy_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    leverage_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    included: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    override_mode: Mapped[str] = mapped_column(String(40), nullable=False, default="normal")
    note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class PortfolioSavedViewRecord(Base):
    """Tenant-scoped saved dashboard filters that can be personal or shared."""

    __tablename__ = "portfolio_saved_views"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_by: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_by_name: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    portfolio_view: Mapped[str] = mapped_column(String(40), nullable=False)
    is_shared: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
