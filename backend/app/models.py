from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

MONEY = Numeric(20, 6)
RATE = Numeric(20, 10)


def enum_values(enum_type: type[StrEnum]) -> list[str]:
    return [str(member.value) for member in enum_type]


class AccountType(StrEnum):
    REVENUE_EXPENSE = "revenue_expense"
    BALANCE_SHEET = "balance_sheet"
    RETAINED_EARNINGS = "retained_earnings"
    TITLE = "title"


class JournalStatus(StrEnum):
    DRAFT = "draft"
    VALIDATED = "validated"
    APPROVED = "approved"
    POSTED = "posted"
    REVERSED = "reversed"
    REJECTED = "rejected"


class PeriodStatus(StrEnum):
    OPEN = "open"
    SOFT_CLOSED = "soft_closed"
    CLOSED = "closed"


class RunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


def uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(Uuid, primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Company(Base, TimestampMixin):
    __tablename__ = "companies"
    id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(20), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    base_currency_code: Mapped[str] = mapped_column(String(3), ForeignKey("currencies.code"))
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Singapore")
    rounding_places: Mapped[int] = mapped_column(Integer, default=2)
    use_bankers_rounding: Mapped[bool] = mapped_column(Boolean, default=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (
        CheckConstraint("rounding_places between 0 and 6", name="companies_rounding_places_check"),
    )


class Currency(Base):
    __tablename__ = "currencies"
    code: Mapped[str] = mapped_column(String(3), primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    minor_units: Mapped[int] = mapped_column(Integer, default=2)
    __table_args__ = (
        CheckConstraint("minor_units between 0 and 6", name="currencies_minor_units_check"),
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = uuid_pk()
    email: Mapped[str] = mapped_column(String(254), unique=True)
    display_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Permission(Base):
    __tablename__ = "permissions"
    code: Mapped[str] = mapped_column(String(80), primary_key=True)
    description: Mapped[str] = mapped_column(String(200))
    legacy_number: Mapped[int | None] = mapped_column(Integer, unique=True)


class Role(Base, TimestampMixin):
    __tablename__ = "roles"
    id: Mapped[uuid.UUID] = uuid_pk()
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(80))
    system: Mapped[bool] = mapped_column(Boolean, default=False)
    __table_args__ = (
        UniqueConstraint("company_id", "id"),
        UniqueConstraint("company_id", "name"),
    )


class RolePermission(Base):
    __tablename__ = "role_permissions"
    company_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    role_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    permission_code: Mapped[str] = mapped_column(
        ForeignKey("permissions.code", ondelete="CASCADE"), primary_key=True
    )
    __table_args__ = (
        ForeignKeyConstraint(
            ["company_id", "role_id"], ["roles.company_id", "roles.id"], ondelete="CASCADE"
        ),
    )


class Membership(Base, TimestampMixin):
    __tablename__ = "memberships"
    company_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (
        ForeignKeyConstraint(
            ["company_id", "role_id"], ["roles.company_id", "roles.id"], ondelete="CASCADE"
        ),
    )


class FiscalYear(Base, TimestampMixin):
    __tablename__ = "fiscal_years"
    id: Mapped[uuid.UUID] = uuid_pk()
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"))
    label: Mapped[str] = mapped_column(String(40))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        UniqueConstraint("company_id", "id"),
        UniqueConstraint("company_id", "label"),
        CheckConstraint("end_date >= start_date", name="fiscal_years_check"),
    )


class FiscalPeriod(Base, TimestampMixin):
    __tablename__ = "fiscal_periods"
    id: Mapped[uuid.UUID] = uuid_pk()
    company_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    fiscal_year_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    period_no: Mapped[int] = mapped_column(Integer)
    label: Mapped[str] = mapped_column(String(40))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    status: Mapped[PeriodStatus] = mapped_column(
        Enum(PeriodStatus, values_callable=enum_values), default=PeriodStatus.OPEN
    )
    __table_args__ = (
        ForeignKeyConstraint(
            ["company_id", "fiscal_year_id"],
            ["fiscal_years.company_id", "fiscal_years.id"],
            ondelete="CASCADE",
        ),
        UniqueConstraint("company_id", "id"),
        UniqueConstraint("company_id", "fiscal_year_id", "period_no"),
        CheckConstraint("period_no between 1 and 18", name="fiscal_periods_period_no_check"),
        CheckConstraint("end_date >= start_date", name="fiscal_periods_check"),
    )


class Account(Base, TimestampMixin):
    __tablename__ = "accounts"
    id: Mapped[uuid.UUID] = uuid_pk()
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"))
    code: Mapped[str] = mapped_column(String(30))
    name: Mapped[str] = mapped_column(String(160))
    account_type: Mapped[AccountType] = mapped_column(
        Enum(AccountType, values_callable=enum_values)
    )
    currency_code: Mapped[str] = mapped_column(ForeignKey("currencies.code"))
    postable: Mapped[bool] = mapped_column(Boolean, default=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (
        UniqueConstraint("company_id", "id"),
        UniqueConstraint("company_id", "code"),
        CheckConstraint(
            "(account_type = 'title' and postable = false) or account_type <> 'title'",
            name="ck_title_not_postable",
        ),
        Index(
            "uq_one_retained_earnings_per_company",
            "company_id",
            unique=True,
            postgresql_where=(account_type == AccountType.RETAINED_EARNINGS),
        ),
    )


class ExchangeRate(Base, TimestampMixin):
    __tablename__ = "exchange_rates"
    id: Mapped[uuid.UUID] = uuid_pk()
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"))
    currency_code: Mapped[str] = mapped_column(ForeignKey("currencies.code"))
    effective_date: Mapped[date] = mapped_column(Date)
    rate_to_base: Mapped[Decimal] = mapped_column(RATE)
    source: Mapped[str] = mapped_column(String(100), default="manual")
    __table_args__ = (
        UniqueConstraint("company_id", "currency_code", "effective_date"),
        CheckConstraint("rate_to_base > 0", name="exchange_rates_rate_to_base_check"),
    )


class NumberSequence(Base):
    __tablename__ = "number_sequences"
    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), primary_key=True
    )
    name: Mapped[str] = mapped_column(String(40), primary_key=True)
    prefix: Mapped[str] = mapped_column(String(20), default="")
    next_value: Mapped[int] = mapped_column(Integer, default=1)
    padding: Mapped[int] = mapped_column(Integer, default=6)
    __table_args__ = (
        CheckConstraint(
            "next_value > 0 and padding between 1 and 18", name="number_sequences_check"
        ),
    )


class JournalBatch(Base, TimestampMixin):
    __tablename__ = "journal_batches"
    id: Mapped[uuid.UUID] = uuid_pk()
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"))
    batch_no: Mapped[str] = mapped_column(String(40))
    description: Mapped[str] = mapped_column(String(250), default="")
    status: Mapped[JournalStatus] = mapped_column(
        Enum(JournalStatus, values_callable=enum_values), default=JournalStatus.DRAFT
    )
    created_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    approved_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, default=1)
    __table_args__ = (
        UniqueConstraint("company_id", "id"),
        UniqueConstraint("company_id", "batch_no"),
        CheckConstraint("version > 0", name="journal_batches_version_check"),
    )
    entries: Mapped[list[JournalEntry]] = relationship(
        back_populates="batch", cascade="all, delete-orphan"
    )


class JournalEntry(Base, TimestampMixin):
    __tablename__ = "journal_entries"
    id: Mapped[uuid.UUID] = uuid_pk()
    company_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    batch_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    entry_no: Mapped[str] = mapped_column(String(40))
    entry_date: Mapped[date] = mapped_column(Date)
    posting_date: Mapped[date] = mapped_column(Date)
    fiscal_period_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    reference: Mapped[str] = mapped_column(String(80), default="")
    description: Mapped[str] = mapped_column(String(250))
    status: Mapped[JournalStatus] = mapped_column(
        Enum(JournalStatus, values_callable=enum_values), default=JournalStatus.DRAFT
    )
    reversal_of_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    created_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        ForeignKeyConstraint(
            ["company_id", "batch_id"],
            ["journal_batches.company_id", "journal_batches.id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["company_id", "fiscal_period_id"],
            ["fiscal_periods.company_id", "fiscal_periods.id"],
        ),
        ForeignKeyConstraint(
            ["company_id", "reversal_of_id"],
            ["journal_entries.company_id", "journal_entries.id"],
        ),
        UniqueConstraint("company_id", "id"),
        UniqueConstraint("company_id", "entry_no"),
    )
    batch: Mapped[JournalBatch] = relationship(back_populates="entries")
    lines: Mapped[list[JournalLine]] = relationship(
        back_populates="entry", cascade="all, delete-orphan", order_by="JournalLine.line_no"
    )


class JournalLine(Base, TimestampMixin):
    __tablename__ = "journal_lines"
    id: Mapped[uuid.UUID] = uuid_pk()
    company_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    entry_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    line_no: Mapped[int] = mapped_column(Integer)
    account_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    description: Mapped[str] = mapped_column(String(250), default="")
    currency_code: Mapped[str] = mapped_column(ForeignKey("currencies.code"))
    exchange_rate: Mapped[Decimal] = mapped_column(RATE, default=Decimal("1"))
    debit_original: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"))
    credit_original: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"))
    debit_base: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"))
    credit_base: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"))
    __table_args__ = (
        ForeignKeyConstraint(
            ["company_id", "entry_id"],
            ["journal_entries.company_id", "journal_entries.id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(["company_id", "account_id"], ["accounts.company_id", "accounts.id"]),
        UniqueConstraint("company_id", "entry_id", "line_no"),
        CheckConstraint("line_no > 0", name="journal_lines_line_no_check"),
        CheckConstraint("exchange_rate > 0", name="journal_lines_exchange_rate_check"),
        CheckConstraint("debit_original >= 0 and credit_original >= 0", name="journal_lines_check"),
        CheckConstraint("debit_base >= 0 and credit_base >= 0", name="journal_lines_check1"),
        CheckConstraint(
            "(debit_original > 0 and credit_original = 0) or "
            "(credit_original > 0 and debit_original = 0)",
            name="ck_line_one_original_side",
        ),
        CheckConstraint(
            "(debit_base > 0 and credit_base = 0) or (credit_base > 0 and debit_base = 0)",
            name="ck_line_one_base_side",
        ),
    )
    entry: Mapped[JournalEntry] = relationship(back_populates="lines")


class PostingEvent(Base):
    __tablename__ = "posting_events"
    id: Mapped[uuid.UUID] = uuid_pk()
    company_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    entry_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    posted_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    debit_total: Mapped[Decimal] = mapped_column(MONEY)
    credit_total: Mapped[Decimal] = mapped_column(MONEY)
    digest: Mapped[str] = mapped_column(String(64))
    __table_args__ = (
        ForeignKeyConstraint(
            ["company_id", "entry_id"],
            ["journal_entries.company_id", "journal_entries.id"],
        ),
        UniqueConstraint("company_id", "entry_id"),
        CheckConstraint(
            "debit_total = credit_total and debit_total > 0", name="posting_events_check"
        ),
    )


class PeriodBalance(Base, TimestampMixin):
    __tablename__ = "period_balances"
    company_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    fiscal_period_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    account_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    currency_code: Mapped[str] = mapped_column(String(3), primary_key=True)
    debit_base: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"))
    credit_base: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"))
    debit_original: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"))
    credit_original: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"))
    __table_args__ = (
        ForeignKeyConstraint(
            ["company_id", "fiscal_period_id"],
            ["fiscal_periods.company_id", "fiscal_periods.id"],
        ),
        ForeignKeyConstraint(["company_id", "account_id"], ["accounts.company_id", "accounts.id"]),
        ForeignKeyConstraint(["currency_code"], ["currencies.code"]),
        CheckConstraint(
            "debit_base >= 0 and credit_base >= 0 and debit_original >= 0 and credit_original >= 0",
            name="period_balances_check",
        ),
    )


class Budget(Base, TimestampMixin):
    __tablename__ = "budgets"
    id: Mapped[uuid.UUID] = uuid_pk()
    company_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    fiscal_period_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    account_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    scenario: Mapped[str] = mapped_column(String(60), default="Current")
    currency_code: Mapped[str] = mapped_column(ForeignKey("currencies.code"))
    amount: Mapped[Decimal] = mapped_column(MONEY)
    __table_args__ = (
        ForeignKeyConstraint(
            ["company_id", "fiscal_period_id"],
            ["fiscal_periods.company_id", "fiscal_periods.id"],
        ),
        ForeignKeyConstraint(["company_id", "account_id"], ["accounts.company_id", "accounts.id"]),
        UniqueConstraint(
            "company_id", "fiscal_period_id", "account_id", "scenario", "currency_code"
        ),
    )


class ClosingEvent(Base, TimestampMixin):
    __tablename__ = "closing_events"
    id: Mapped[uuid.UUID] = uuid_pk()
    company_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    fiscal_year_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    retained_earnings_account_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    closing_entry_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    opening_entry_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    reversed_by_entry_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    closed_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    reconciliation: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    __table_args__ = (
        ForeignKeyConstraint(
            ["company_id", "fiscal_year_id"],
            ["fiscal_years.company_id", "fiscal_years.id"],
        ),
        ForeignKeyConstraint(
            ["company_id", "retained_earnings_account_id"],
            ["accounts.company_id", "accounts.id"],
        ),
        ForeignKeyConstraint(
            ["company_id", "closing_entry_id"],
            ["journal_entries.company_id", "journal_entries.id"],
        ),
        ForeignKeyConstraint(
            ["company_id", "opening_entry_id"],
            ["journal_entries.company_id", "journal_entries.id"],
        ),
        ForeignKeyConstraint(
            ["company_id", "reversed_by_entry_id"],
            ["journal_entries.company_id", "journal_entries.id"],
        ),
        UniqueConstraint("company_id", "fiscal_year_id"),
    )


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[uuid.UUID] = uuid_pk()
    company_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("companies.id"))
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    action: Mapped[str] = mapped_column(String(100))
    entity_type: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[str] = mapped_column(String(80))
    correlation_id: Mapped[str] = mapped_column(String(80))
    before: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    after: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    __table_args__ = (Index("ix_audit_company_time", "company_id", "occurred_at"),)


class SavedView(Base, TimestampMixin):
    __tablename__ = "saved_views"
    id: Mapped[uuid.UUID] = uuid_pk()
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    resource: Mapped[str] = mapped_column(String(80))
    name: Mapped[str] = mapped_column(String(100))
    definition: Mapped[dict[str, Any]] = mapped_column(JSON)
    shared: Mapped[bool] = mapped_column(Boolean, default=False)
    __table_args__ = (UniqueConstraint("company_id", "user_id", "resource", "name"),)


class UserPreference(Base, TimestampMixin):
    __tablename__ = "user_preferences"
    company_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[dict[str, Any]] = mapped_column(JSON)
    __table_args__ = (
        ForeignKeyConstraint(
            ["company_id", "user_id"],
            ["memberships.company_id", "memberships.user_id"],
            ondelete="CASCADE",
        ),
    )


class ReportDefinition(Base, TimestampMixin):
    __tablename__ = "report_definitions"
    id: Mapped[uuid.UUID] = uuid_pk()
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(160))
    report_type: Mapped[str] = mapped_column(String(60))
    definition: Mapped[dict[str, Any]] = mapped_column(JSON)
    legacy_spec: Mapped[str | None] = mapped_column(Text)
    legacy_template: Mapped[str | None] = mapped_column(Text)
    conversion_status: Mapped[str | None] = mapped_column(String(40))
    is_template: Mapped[bool] = mapped_column(Boolean, default=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    __table_args__ = (
        UniqueConstraint("company_id", "id"),
        UniqueConstraint("company_id", "name"),
        CheckConstraint(
            "report_type IN ('structured', 'legacy')",
            name="ck_report_definitions_report_definition_type",
        ),
        CheckConstraint(
            "conversion_status IS NULL OR conversion_status IN "
            "('compatible', 'partial', 'manual', 'converted')",
            name="ck_report_definitions_report_definition_conversion_status",
        ),
        CheckConstraint(
            "version >= 1", name="ck_report_definitions_report_definition_version_positive"
        ),
    )


class ReportRun(Base, TimestampMixin):
    __tablename__ = "report_runs"
    id: Mapped[uuid.UUID] = uuid_pk()
    company_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    report_definition_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    report_type: Mapped[str] = mapped_column(String(60))
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON)
    status: Mapped[RunStatus] = mapped_column(
        Enum(RunStatus, values_callable=enum_values), default=RunStatus.QUEUED
    )
    requested_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    result_digest: Mapped[str | None] = mapped_column(String(64))
    artifact_path: Mapped[str | None] = mapped_column(String(500))
    error: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (
        ForeignKeyConstraint(
            ["company_id", "report_definition_id"],
            ["report_definitions.company_id", "report_definitions.id"],
        ),
    )


class OperationJob(Base, TimestampMixin):
    __tablename__ = "operation_jobs"
    id: Mapped[uuid.UUID] = uuid_pk()
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String(80))
    status: Mapped[RunStatus] = mapped_column(
        Enum(RunStatus, values_callable=enum_values), default=RunStatus.QUEUED
    )
    requested_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    error: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (
        CheckConstraint("progress between 0 and 100", name="operation_jobs_progress_check"),
    )


class MigrationRun(Base, TimestampMixin):
    __tablename__ = "migration_runs"
    id: Mapped[uuid.UUID] = uuid_pk()
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"))
    source_path: Mapped[str] = mapped_column(String(1000))
    source_digest: Mapped[str] = mapped_column(String(64))
    status: Mapped[RunStatus] = mapped_column(
        Enum(RunStatus, values_callable=enum_values), default=RunStatus.QUEUED
    )
    dry_run: Mapped[bool] = mapped_column(Boolean, default=True)
    requested_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    counts: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    reconciliation: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    __table_args__ = (
        UniqueConstraint("company_id", "id"),
        UniqueConstraint("company_id", "source_digest", "dry_run"),
        CheckConstraint(
            "char_length(source_digest) = 64", name="migration_runs_digest_length_check"
        ),
    )


class MigrationStagingRecord(Base):
    __tablename__ = "migration_staging_records"
    id: Mapped[uuid.UUID] = uuid_pk()
    company_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    migration_run_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    source_table: Mapped[str] = mapped_column(String(80))
    source_record: Mapped[int] = mapped_column(Integer)
    natural_key: Mapped[str | None] = mapped_column(String(250))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    severity: Mapped[str] = mapped_column(String(20), default="ok")
    issues: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    __table_args__ = (
        ForeignKeyConstraint(
            ["company_id", "migration_run_id"],
            ["migration_runs.company_id", "migration_runs.id"],
            ondelete="CASCADE",
        ),
        UniqueConstraint("company_id", "migration_run_id", "source_table", "source_record"),
        CheckConstraint("source_record > 0", name="migration_staging_source_record_check"),
        CheckConstraint(
            "severity in ('ok', 'warning', 'error')",
            name="migration_staging_severity_check",
        ),
        CheckConstraint(
            "source_table in ('GLACCNT', 'GLACCNX', 'GLMAIN', 'GLTRANS', 'GLGP', 'GLREP')",
            name="migration_staging_source_table_check",
        ),
    )


Index(
    "uq_one_reversal_per_entry", JournalEntry.company_id, JournalEntry.reversal_of_id, unique=True
)
