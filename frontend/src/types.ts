export type CompanyAccess = {
  id: string;
  code: string;
  name: string;
  base_currency_code: string;
  role: string;
  capabilities: string[];
};

export type Me = {
  id: string;
  email: string;
  display_name: string;
  companies: CompanyAccess[];
};

export type Account = {
  id: string;
  code: string;
  name: string;
  account_type: string;
  currency_code: string;
  postable: boolean;
  active: boolean;
};

export type Period = {
  id: string;
  fiscal_year_id: string;
  period_no: number;
  label: string;
  start_date: string;
  end_date: string;
  status: string;
};

export type FiscalYear = {
  id: string;
  label: string;
  start_date: string;
  end_date: string;
  closed_at: string | null;
};

export type Budget = {
  id: string;
  fiscal_period_id: string;
  account_id: string;
  scenario: string;
  currency_code: string;
  amount: string;
};

export type ClosePreview = {
  fiscal_year_id: string;
  closing_period_id: string;
  opening_period_id: string;
  profit_loss: string;
  retained_earnings_account_id: string;
  closing_lines: number;
  opening_lines: number;
  balanced: boolean;
};

export type ReportRun = {
  id: string;
  report_type: string;
  parameters: Record<string, unknown>;
  status: string;
  result_digest: string | null;
  error: string | null;
  created_at: string;
};

export type ReportResult = {
  run_id: string;
  title: string;
  digest: string;
  columns: string[];
  rows: Record<string, unknown>[];
};

export type AdminMembership = {
  user_id: string;
  email: string;
  display_name: string;
  role_id: string;
  role_name: string;
  active: boolean;
};

export type AdminRole = { id: string; name: string; system: boolean };
export type Permission = { code: string; description: string };
export type CompanySettings = {
  id: string;
  code: string;
  name: string;
  base_currency_code: string;
  timezone: string;
  rounding_places: number;
  use_bankers_rounding: boolean;
};
export type AuditEvent = { id: string; occurred_at: string; action: string; entity_type: string; entity_id: string };
export type Operation = { id: string; kind: string; status: string; progress: number; result: Record<string, unknown> | null; error: string | null; created_at: string };

export type CustomReportColumn = {
  key: string;
  label: string;
  kind: "balance" | "budget" | "formula";
  period_id?: string | null;
  legacy_period_no?: number | null;
  period_from?: number | null;
  scope: "period" | "ytd" | "range";
  scenario?: string;
  formula?: string | null;
};

export type CustomReportRow = {
  key: string;
  label: string;
  kind: "account" | "range" | "formula" | "heading" | "spacer";
  account_code?: string | null;
  account_from?: string | null;
  account_to?: string | null;
  formula?: string | null;
  bold?: boolean;
  indent?: number;
};

export type CustomReportDefinitionData = {
  title: string;
  columns: CustomReportColumn[];
  rows: CustomReportRow[];
  sections: { title: string; row_keys: string[]; page_break_before?: boolean }[];
  formatting: { decimals?: number; [key: string]: unknown };
};

export type CustomReportDefinition = {
  id: string;
  name: string;
  report_type: string;
  definition: CustomReportDefinitionData;
  conversion_status: string | null;
  is_template: boolean;
  version: number;
  created_at: string;
  updated_at: string;
};

export type LegacyConversion = {
  status: "compatible" | "partial" | "manual";
  definition: CustomReportDefinitionData | null;
  warnings: string[];
};

export type MigrationException = {
  id: string;
  source_table: string;
  source_record: number;
  natural_key: string | null;
  severity: "warning" | "error";
  issues: { code: string; message: string; field?: string | null; blocking: boolean }[];
};

export type MigrationRun = {
  id: string;
  source_path: string;
  source_digest: string;
  status: string;
  dry_run: boolean;
  counts: {
    records?: number;
    errors?: number;
    warnings?: number;
    tables?: Record<string, number>;
    applied_accounts?: number;
    applied_posted_batches?: number;
    applied_draft_batches?: number;
  };
  reconciliation: {
    apply_ready?: boolean;
    ledger_balanced?: boolean;
    account_periods_match?: boolean;
    opening_balance_net?: string;
    ledger_debits?: string;
    ledger_credits?: string;
    blocking_reason?: string;
  };
  staging_records: MigrationException[];
  created_at: string;
};

export type JournalLine = {
  id: string;
  line_no: number;
  account_id: string;
  description: string;
  currency_code: string;
  exchange_rate: string;
  debit_original: string;
  credit_original: string;
  debit_base: string;
  credit_base: string;
};

export type JournalEntry = {
  id: string;
  entry_no: string;
  entry_date: string;
  posting_date: string;
  fiscal_period_id: string;
  reference: string;
  description: string;
  status: string;
  reversal_of_id: string | null;
  lines: JournalLine[];
};

export type JournalBatch = {
  id: string;
  batch_no: string;
  description: string;
  status: string;
  created_at: string;
  entries: JournalEntry[];
};
