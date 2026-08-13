import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.models import AccountType, JournalStatus, PeriodStatus, RunStatus


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TokenRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(ORMModel):
    id: uuid.UUID
    email: EmailStr
    display_name: str


class CompanyOut(ORMModel):
    id: uuid.UUID
    code: str
    name: str
    base_currency_code: str


class CompanyAccessOut(CompanyOut):
    role: str
    capabilities: list[str]


class MeOut(UserOut):
    companies: list[CompanyAccessOut]


class FiscalPeriodCreate(BaseModel):
    period_no: int = Field(ge=1, le=18)
    label: str = Field(min_length=1, max_length=40)
    start_date: date
    end_date: date


class FiscalYearCreate(BaseModel):
    label: str = Field(min_length=1, max_length=40)
    start_date: date
    end_date: date
    periods: list[FiscalPeriodCreate] = Field(min_length=1, max_length=18)

    @model_validator(mode="after")
    def validate_periods(self) -> "FiscalYearCreate":
        expected = list(range(1, len(self.periods) + 1))
        if [period.period_no for period in self.periods] != expected:
            raise ValueError("Period numbers must be contiguous and start at 1")
        if self.end_date < self.start_date:
            raise ValueError("Fiscal year end must not precede start")
        previous_end: date | None = None
        for period in self.periods:
            if period.end_date < period.start_date:
                raise ValueError("Period end must not precede start")
            if previous_end is not None and period.start_date <= previous_end:
                raise ValueError("Fiscal periods must be ordered and non-overlapping")
            if period.start_date < self.start_date or period.end_date > self.end_date:
                raise ValueError("Fiscal period must fall inside the fiscal year")
            previous_end = period.end_date
        return self


class FiscalPeriodOut(ORMModel):
    id: uuid.UUID
    fiscal_year_id: uuid.UUID
    period_no: int
    label: str
    start_date: date
    end_date: date
    status: PeriodStatus


class FiscalYearOut(ORMModel):
    id: uuid.UUID
    label: str
    start_date: date
    end_date: date
    closed_at: datetime | None


class AccountCreate(BaseModel):
    code: str = Field(min_length=1, max_length=30)
    name: str = Field(min_length=1, max_length=160)
    account_type: AccountType
    currency_code: str = Field(min_length=3, max_length=3)
    postable: bool = True

    @model_validator(mode="after")
    def title_is_not_postable(self) -> "AccountCreate":
        if self.account_type == AccountType.TITLE and self.postable:
            raise ValueError("Title accounts cannot be postable")
        return self


class AccountOut(ORMModel):
    id: uuid.UUID
    code: str
    name: str
    account_type: AccountType
    currency_code: str
    postable: bool
    active: bool


class AccountUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    postable: bool = True
    active: bool = True


class CompanySettingsOut(ORMModel):
    id: uuid.UUID
    code: str
    name: str
    base_currency_code: str
    timezone: str
    rounding_places: int
    use_bankers_rounding: bool


class CompanySettingsUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    timezone: str = Field(min_length=1, max_length=64)
    rounding_places: int = Field(ge=0, le=6)
    use_bankers_rounding: bool = True


class PermissionOut(ORMModel):
    code: str
    description: str


class JournalLineCreate(BaseModel):
    account_id: uuid.UUID
    description: str = Field(default="", max_length=250)
    currency_code: str = Field(min_length=3, max_length=3)
    exchange_rate: Decimal = Field(default=Decimal("1"), gt=0, max_digits=20, decimal_places=10)
    debit: Decimal = Field(default=Decimal("0"), ge=0, max_digits=20, decimal_places=6)
    credit: Decimal = Field(default=Decimal("0"), ge=0, max_digits=20, decimal_places=6)

    @model_validator(mode="after")
    def one_side_only(self) -> "JournalLineCreate":
        if (self.debit > 0) == (self.credit > 0):
            raise ValueError("Exactly one of debit or credit must be positive")
        return self


class JournalEntryCreate(BaseModel):
    entry_date: date
    posting_date: date
    fiscal_period_id: uuid.UUID
    reference: str = Field(default="", max_length=80)
    description: str = Field(min_length=1, max_length=250)
    lines: list[JournalLineCreate] = Field(min_length=2)


class JournalBatchCreate(BaseModel):
    batch_no: str | None = Field(default=None, max_length=40)
    description: str = Field(default="", max_length=250)
    entries: list[JournalEntryCreate] = Field(min_length=1)


class JournalLineOut(ORMModel):
    id: uuid.UUID
    line_no: int
    account_id: uuid.UUID
    description: str
    currency_code: str
    exchange_rate: Decimal
    debit_original: Decimal
    credit_original: Decimal
    debit_base: Decimal
    credit_base: Decimal


class JournalEntryOut(ORMModel):
    id: uuid.UUID
    entry_no: str
    entry_date: date
    posting_date: date
    fiscal_period_id: uuid.UUID
    reference: str
    description: str
    status: JournalStatus
    reversal_of_id: uuid.UUID | None
    lines: list[JournalLineOut]


class JournalBatchOut(ORMModel):
    id: uuid.UUID
    batch_no: str
    description: str
    status: JournalStatus
    created_at: datetime
    entries: list[JournalEntryOut]


class ReversalRequest(BaseModel):
    posting_date: date
    fiscal_period_id: uuid.UUID
    reason: str = Field(min_length=3, max_length=250)


class TrialBalanceRow(BaseModel):
    account_id: uuid.UUID
    code: str
    name: str
    debit: Decimal
    credit: Decimal
    net: Decimal


class BudgetUpsert(BaseModel):
    fiscal_period_id: uuid.UUID
    account_id: uuid.UUID
    scenario: str = Field(default="Current", min_length=1, max_length=60)
    currency_code: str = Field(min_length=3, max_length=3)
    amount: Decimal = Field(max_digits=20, decimal_places=6)


class BudgetOut(ORMModel):
    id: uuid.UUID
    fiscal_period_id: uuid.UUID
    account_id: uuid.UUID
    scenario: str
    currency_code: str
    amount: Decimal


class CloseRequest(BaseModel):
    opening_period_id: uuid.UUID
    reason: str = Field(default="Approved fiscal-year close", min_length=3, max_length=250)


class CompensatingCloseRequest(BaseModel):
    fiscal_period_id: uuid.UUID
    posting_date: date
    reason: str = Field(min_length=3, max_length=250)


class ClosePreview(BaseModel):
    fiscal_year_id: uuid.UUID
    closing_period_id: uuid.UUID
    opening_period_id: uuid.UUID
    profit_loss: Decimal
    retained_earnings_account_id: uuid.UUID
    closing_lines: int
    opening_lines: int
    balanced: bool


class CloseResult(ClosePreview):
    closing_event_id: uuid.UUID
    batch_id: uuid.UUID | None
    closing_entry_id: uuid.UUID | None
    opening_entry_id: uuid.UUID | None


class IntegrityResult(BaseModel):
    ok: bool
    checks: list[dict[str, Any]]


class ReportRequest(BaseModel):
    report_type: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    format: str = Field(default="json", pattern="^(json|csv|xlsx|pdf)$")


class ReportRunOut(ORMModel):
    id: uuid.UUID
    report_type: str
    parameters: dict[str, Any]
    status: RunStatus
    result_digest: str | None
    error: str | None
    created_at: datetime


class SavedViewCreate(BaseModel):
    resource: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=100)
    definition: dict[str, Any]
    shared: bool = False


class SavedViewOut(ORMModel):
    id: uuid.UUID
    user_id: uuid.UUID
    resource: str
    name: str
    definition: dict[str, Any]
    shared: bool


class PreferenceUpsert(BaseModel):
    value: dict[str, Any]


class PreferenceOut(ORMModel):
    key: str
    value: dict[str, Any]


class AdminUserCreate(BaseModel):
    email: EmailStr
    display_name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=12, max_length=200)
    role_id: uuid.UUID


class MembershipOut(BaseModel):
    user_id: uuid.UUID
    email: EmailStr
    display_name: str
    role_id: uuid.UUID
    role_name: str
    active: bool


class MembershipUpdate(BaseModel):
    role_id: uuid.UUID
    active: bool = True


class RoleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    permissions: list[str] = Field(default_factory=list)


class RoleOut(ORMModel):
    id: uuid.UUID
    name: str
    system: bool


class RolePermissionsUpdate(BaseModel):
    permissions: list[str]


class BulkJournalRequest(BaseModel):
    batch_ids: list[uuid.UUID] = Field(min_length=1, max_length=100)
    action: str = Field(pattern="^(validate|approve|post)$")


class BulkResult(BaseModel):
    succeeded: list[uuid.UUID]
    failed: list[dict[str, Any]]


class OperationRequest(BaseModel):
    kind: str = Field(pattern="^(integrity|trial_balance)$")
    parameters: dict[str, Any] = Field(default_factory=dict)


class OperationOut(ORMModel):
    id: uuid.UUID
    kind: str
    status: RunStatus
    parameters: dict[str, Any]
    progress: int
    result: dict[str, Any] | None
    error: str | None
    created_at: datetime


class CustomReportColumn(BaseModel):
    key: str = Field(pattern=r"^[a-z][a-z0-9_]{0,39}$")
    label: str = Field(min_length=1, max_length=100)
    kind: Literal["balance", "budget", "formula"]
    period_id: uuid.UUID | None = None
    legacy_period_no: int | None = Field(default=None, ge=1, le=18)
    period_from: int | None = Field(default=None, ge=1, le=18)
    scope: Literal["period", "ytd", "range"] = "period"
    scenario: str = Field(default="Current", min_length=1, max_length=60)
    formula: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def formula_required_for_formula_column(self) -> "CustomReportColumn":
        if self.kind == "formula" and not self.formula:
            raise ValueError("Formula columns require a formula")
        if self.scope == "range" and self.period_from is None:
            raise ValueError("Range columns require period_from")
        return self


class CustomReportRow(BaseModel):
    key: str = Field(pattern=r"^[a-z][a-z0-9_]{0,39}$")
    label: str = Field(default="", max_length=160)
    kind: Literal["account", "range", "formula", "heading", "spacer"]
    account_code: str | None = Field(default=None, max_length=30)
    account_from: str | None = Field(default=None, max_length=30)
    account_to: str | None = Field(default=None, max_length=30)
    formula: str | None = Field(default=None, max_length=500)
    bold: bool = False
    indent: int = Field(default=0, ge=0, le=8)

    @model_validator(mode="after")
    def required_row_fields(self) -> "CustomReportRow":
        if self.kind == "account" and not self.account_code:
            raise ValueError("Account rows require account_code")
        if self.kind == "range" and (not self.account_from or not self.account_to):
            raise ValueError("Range rows require account_from and account_to")
        if self.kind == "formula" and not self.formula:
            raise ValueError("Formula rows require a formula")
        return self


class CustomReportSection(BaseModel):
    title: str = Field(default="", max_length=160)
    row_keys: list[str] = Field(min_length=1, max_length=200)
    page_break_before: bool = False


class CustomReportDefinitionData(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    columns: list[CustomReportColumn] = Field(min_length=1, max_length=20)
    rows: list[CustomReportRow] = Field(min_length=1, max_length=200)
    sections: list[CustomReportSection] = Field(default_factory=list, max_length=30)
    formatting: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def unique_keys_and_valid_sections(self) -> "CustomReportDefinitionData":
        column_keys = [column.key for column in self.columns]
        row_keys = [row.key for row in self.rows]
        if len(set(column_keys)) != len(column_keys):
            raise ValueError("Column keys must be unique")
        if len(set(row_keys)) != len(row_keys):
            raise ValueError("Row keys must be unique")
        unknown = {key for section in self.sections for key in section.row_keys} - set(row_keys)
        if unknown:
            raise ValueError(f"Sections reference unknown rows: {', '.join(sorted(unknown))}")
        return self


class CustomReportCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    definition: CustomReportDefinitionData
    is_template: bool = False


class CustomReportUpdate(CustomReportCreate):
    version: int = Field(ge=1)


class CustomReportOut(ORMModel):
    id: uuid.UUID
    name: str
    report_type: str
    definition: dict[str, Any]
    conversion_status: str | None
    is_template: bool
    version: int
    created_at: datetime
    updated_at: datetime


class CustomReportPreview(BaseModel):
    definition: CustomReportDefinitionData
    parameters: dict[str, Any] = Field(default_factory=dict)


class CustomReportRunRequest(BaseModel):
    parameters: dict[str, Any] = Field(default_factory=dict)
    format: str = Field(default="json", pattern="^(json|csv|xlsx|pdf)$")


class LegacyReportImport(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    spec: str = Field(min_length=1, max_length=100_000)
    template: str = Field(default="", max_length=1_000_000)
    is_template: bool = False


class LegacyConversionPreview(BaseModel):
    status: Literal["compatible", "partial", "manual"]
    definition: CustomReportDefinitionData | None
    warnings: list[str]


class MigrationStagingOut(ORMModel):
    id: uuid.UUID
    source_table: str
    source_record: int
    natural_key: str | None
    severity: str
    issues: list[dict[str, Any]]


class MigrationRunOut(ORMModel):
    id: uuid.UUID
    source_path: str
    source_digest: str
    status: RunStatus
    dry_run: bool
    counts: dict[str, Any]
    reconciliation: dict[str, Any]
    created_at: datetime
    staging_records: list[MigrationStagingOut] = Field(default_factory=list)


class MigrationApplyRequest(BaseModel):
    source_digest: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    confirmation: Literal["APPLY"]
