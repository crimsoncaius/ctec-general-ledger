import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { AccountManager } from "./AccountManager";
import { AdministrationSettings } from "./AdministrationSettings";
import { api, apiDownload, apiUpload } from "./api";
import { CustomReportDesigner } from "./CustomReportDesigner";
import {
  AmountCell,
  Banner,
  Badge,
  Button,
  Checkbox,
  CompanySwitcher,
  Dialog,
  DigestValue,
  EmptyState,
  Field,
  Icon,
  Input,
  KeyValueList,
  PageHeader,
  ProgressBar,
  Select,
  SidebarNav,
  StatusPill,
  type DataState,
  type LedgerStatus,
  type NavGroup,
} from "./design-system";
import { FiscalCalendarManager } from "./FiscalCalendarManager";
import { LegacyMigrationPanel } from "./LegacyMigrationPanel";
import type {
  Account,
  AdminMembership,
  AdminRole,
  AuditEvent,
  Budget,
  ClosePreview,
  CompanyAccess,
  FiscalYear,
  JournalBatch,
  JournalEntry,
  Me,
  Operation,
  Period,
  ReportResult,
  ReportRun,
} from "./types";

type Page =
  | "overview"
  | "accounts"
  | "journals"
  | "inquiry"
  | "fiscal"
  | "planning"
  | "reports"
  | "designer"
  | "admin";

const PAGE_TITLES: Record<Page, string> = {
  overview: "Ledger overview",
  accounts: "Chart of accounts",
  journals: "Journal preparation and approval",
  inquiry: "Posted inquiry and reversal",
  fiscal: "Fiscal calendars",
  planning: "Budgets and fiscal close",
  reports: "Standard reports",
  designer: "Report designer",
  admin: "Administration and migration",
};

function Login({ onLogin }: { onLogin: (token: string, me: Me) => void }) {
  const [email, setEmail] = useState("admin@example.com");
  const [password, setPassword] = useState("CTec-Demo-Admin-2026!");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const result = await api<{ access_token: string }>("/auth/token", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      const me = await api<Me>("/auth/me", {}, result.access_token);
      onLogin(result.access_token, me);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Sign-in failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="login-layout">
      <section className="login-story" aria-label="Product introduction">
        <div className="login-wordmark">
          <span>CT</span>
          <strong>CTec Ledger</strong>
        </div>
        <p className="eyebrow">CONTROLLED GENERAL LEDGER</p>
        <h1>Financial truth, with a trail behind it.</h1>
        <p>
          Every posting, close, and migration records who acted, what changed,
          and whether it reconciled.
        </p>
        <p className="access-note">
          Access is scoped to your company memberships.
        </p>
      </section>
      <section className="login-panel">
        <div className="login-card">
          <p className="eyebrow">SECURE ACCESS</p>
          <h2 aria-label="Welcome back">Sign in</h2>
          <p className="muted">
            Your workspace opens once memberships have loaded.
          </p>
          {error ? <Banner tone="danger">{error}</Banner> : null}
          <form onSubmit={submit}>
            <Field label="Email" htmlFor="login-email" required>
              <Input
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                autoComplete="username"
              />
            </Field>
            <Field label="Password" htmlFor="login-password" required>
              <Input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                autoComplete="current-password"
              />
            </Field>
            <Button
              type="submit"
              variant="primary"
              icon="log-in"
              busy={busy}
              fullWidth
            >
              Sign in
            </Button>
          </form>
          <p className="local-note">
            Credentials are never stored in this browser session.
          </p>
        </div>
      </section>
    </main>
  );
}

type ComposerProps = {
  accounts: Account[];
  periods: Period[];
  onCreated: () => Promise<void>;
  token: string;
  companyId: string;
};

function JournalComposer({
  accounts,
  periods,
  onCreated,
  token,
  companyId,
}: ComposerProps) {
  const postable = accounts.filter(
    (account) => account.active && account.postable,
  );
  const [description, setDescription] = useState("Cash sale");
  const [amount, setAmount] = useState("100.00");
  const [periodId, setPeriodId] = useState("");
  const [debitAccount, setDebitAccount] = useState("");
  const [creditAccount, setCreditAccount] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const selectedPeriodId = periodId || periods[0]?.id || "";
  const selectedDebitAccount = debitAccount || postable[0]?.id || "";
  const selectedCreditAccount = creditAccount || postable[1]?.id || "";
  const period = periods.find((item) => item.id === selectedPeriodId);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!period || selectedDebitAccount === selectedCreditAccount) {
      setError("Choose a period and two different accounts.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await api(
        "/journals",
        {
          method: "POST",
          body: JSON.stringify({
            description,
            entries: [
              {
                entry_date: period.start_date,
                posting_date: period.start_date,
                fiscal_period_id: period.id,
                reference: "WEB-DEMO",
                description,
                lines: [
                  {
                    account_id: selectedDebitAccount,
                    currency_code: "SGD",
                    debit: amount,
                    credit: "0",
                  },
                  {
                    account_id: selectedCreditAccount,
                    currency_code: "SGD",
                    debit: "0",
                    credit: amount,
                  },
                ],
              },
            ],
          }),
        },
        token,
        companyId,
      );
      await onCreated();
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Journal could not be created",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="composer" onSubmit={submit}>
      <div className="section-heading">
        <div>
          <p className="eyebrow">NEW BATCH</p>
          <h3>Balanced journal</h3>
        </div>
        <StatusPill status="draft" />
      </div>
      {error ? <Banner tone="danger">{error}</Banner> : null}
      <Field label="Description" htmlFor="journal-description" required>
        <Input
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          required
        />
      </Field>
      <div className="form-grid">
        <Field label="Fiscal period" htmlFor="journal-period" required>
          <Select
            value={selectedPeriodId}
            onChange={(event) => setPeriodId(event.target.value)}
          >
            {periods.map((item) => (
              <option value={item.id} key={item.id}>
                {item.label} · {item.status}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Amount" htmlFor="journal-amount" required>
          <Input
            numeric
            inputMode="decimal"
            suffix="SGD"
            value={amount}
            onChange={(event) => setAmount(event.target.value)}
            required
          />
        </Field>
        <Field label="Debit account" htmlFor="journal-debit" required>
          <Select
            value={selectedDebitAccount}
            onChange={(event) => setDebitAccount(event.target.value)}
          >
            {postable.map((account) => (
              <option value={account.id} key={account.id}>
                {account.code} · {account.name}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Credit account" htmlFor="journal-credit" required>
          <Select
            value={selectedCreditAccount}
            onChange={(event) => setCreditAccount(event.target.value)}
          >
            {postable.map((account) => (
              <option value={account.id} key={account.id}>
                {account.code} · {account.name}
              </option>
            ))}
          </Select>
        </Field>
      </div>
      <Button
        type="submit"
        variant="primary"
        busy={busy}
        disabled={!period || !selectedDebitAccount || !selectedCreditAccount}
      >
        Create draft batch
      </Button>
    </form>
  );
}

type WorkspaceProps = { token: string; me: Me; onLogout: () => void };

async function loadWorkspace(
  token: string,
  companyId: string,
  includeBudgets: boolean,
  includeReports: boolean,
) {
  const [accounts, periods, years, batches, budgets, reportRuns] =
    await Promise.all([
      api<Account[]>("/accounts", {}, token, companyId),
      api<Period[]>("/fiscal/periods", {}, token, companyId),
      api<FiscalYear[]>("/fiscal/years", {}, token, companyId),
      api<JournalBatch[]>("/journals", {}, token, companyId),
      includeBudgets
        ? api<Budget[]>("/budgets", {}, token, companyId)
        : Promise.resolve([]),
      includeReports
        ? api<ReportRun[]>("/reports/runs", {}, token, companyId)
        : Promise.resolve([]),
    ]);
  return { accounts, periods, years, batches, budgets, reportRuns };
}

function Workspace({ token, me, onLogout }: WorkspaceProps) {
  const [companyId, setCompanyId] = useState(me.companies[0]?.id ?? "");
  const [page, setPage] = useState<Page>("overview");
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [periods, setPeriods] = useState<Period[]>([]);
  const [years, setYears] = useState<FiscalYear[]>([]);
  const [batches, setBatches] = useState<JournalBatch[]>([]);
  const [budgets, setBudgets] = useState<Budget[]>([]);
  const [reportRuns, setReportRuns] = useState<ReportRun[]>([]);
  const [error, setError] = useState("");
  const [busyAction, setBusyAction] = useState("");
  const [integrityResult, setIntegrityResult] = useState("");
  const [notice, setNotice] = useState<{
    tone: "success" | "warning";
    title: string;
    message: string;
  } | null>(null);
  const [dataState, setDataState] = useState<DataState>("loading");
  const company =
    me.companies.find((item) => item.id === companyId) ?? me.companies[0];
  const capabilities = useMemo(
    () => new Set(company?.capabilities ?? []),
    [company],
  );
  const canManageBudgets = capabilities.has("budgets.manage");
  const canRunReports = capabilities.has("reports.run");
  const canRunCustomReports = capabilities.has("reports.custom.run");
  const canAdmin =
    capabilities.has("users.manage") ||
    capabilities.has("accounts.import") ||
    capabilities.has("audit.view") ||
    capabilities.has("migration.run");
  const postedEntries = useMemo(
    () =>
      batches
        .flatMap((batch) => batch.entries)
        .filter((entry) => entry.status === "posted"),
    [batches],
  );
  const navGroups = useMemo<NavGroup[]>(() => {
    const groups: NavGroup[] = [
      {
        label: "Company",
        items: [
          { id: "overview", label: "overview", icon: "layout-dashboard" },
          {
            id: "accounts",
            label: "accounts",
            icon: "list-tree",
            readOnly: !capabilities.has("accounts.manage"),
          },
          {
            id: "fiscal",
            label: "fiscal",
            icon: "calendar-range",
            readOnly: !capabilities.has("fiscal.manage"),
          },
        ],
      },
      {
        label: "Ledger",
        items: [
          {
            id: "journals",
            label: "journals",
            icon: "file-stack",
            badge: batches.filter((batch) => batch.status !== "posted").length,
            readOnly:
              !capabilities.has("journals.create") &&
              !capabilities.has("journals.approve") &&
              !capabilities.has("journals.post"),
          },
          {
            id: "inquiry",
            label: "inquiry",
            icon: "search",
            badge: postedEntries.length,
            readOnly: !capabilities.has("journals.reverse"),
          },
        ],
      },
    ];
    const planningItems: NavGroup["items"] = [];
    if (canManageBudgets || capabilities.has("fiscal.close"))
      planningItems.push({
        id: "planning",
        label: "planning",
        icon: "scale",
      });
    if (canRunReports)
      planningItems.push({
        id: "reports",
        label: "reports",
        icon: "file-text",
      });
    if (canRunCustomReports)
      planningItems.push({
        id: "designer",
        label: "designer",
        icon: "table-properties",
        readOnly: !capabilities.has("reports.custom.design"),
      });
    if (planningItems.length)
      groups.push({ label: "Planning and reporting", items: planningItems });
    if (canAdmin)
      groups.push({
        label: "Control",
        items: [{ id: "admin", label: "admin", icon: "settings" }],
      });
    return groups;
  }, [
    batches,
    canAdmin,
    canManageBudgets,
    canRunCustomReports,
    canRunReports,
    capabilities,
    postedEntries.length,
  ]);

  const refresh = useCallback(async () => {
    if (!companyId) return;
    setError("");
    setDataState("refreshing");
    try {
      const result = await loadWorkspace(
        token,
        companyId,
        canManageBudgets,
        canRunReports,
      );
      setAccounts(result.accounts);
      setPeriods(result.periods);
      setYears(result.years);
      setBatches(result.batches);
      setBudgets(result.budgets);
      setReportRuns(result.reportRuns);
      setDataState("current");
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Workspace could not be loaded",
      );
      setDataState("failed");
    }
  }, [canManageBudgets, canRunReports, companyId, token]);

  useEffect(() => {
    let ignore = false;
    void loadWorkspace(token, companyId, canManageBudgets, canRunReports)
      .then((result) => {
        if (!ignore) {
          setAccounts(result.accounts);
          setPeriods(result.periods);
          setYears(result.years);
          setBatches(result.batches);
          setBudgets(result.budgets);
          setReportRuns(result.reportRuns);
          setDataState("current");
        }
      })
      .catch((caught: unknown) => {
        if (!ignore) {
          setError(
            caught instanceof Error
              ? caught.message
              : "Workspace could not be loaded",
          );
          setDataState("failed");
        }
      });
    return () => {
      ignore = true;
    };
  }, [canManageBudgets, canRunReports, companyId, token]);

  useEffect(() => {
    function shortcut(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null;
      if (!event.altKey || target?.matches("input, select, textarea")) return;
      const destination: Partial<Record<string, Page>> = {
        j: "journals",
        i: "inquiry",
        r: "reports",
        a: "accounts",
        c: "designer",
      };
      const next = destination[event.key.toLowerCase()];
      if (
        next &&
        (next !== "reports" || canRunReports) &&
        (next !== "designer" || canRunCustomReports)
      ) {
        event.preventDefault();
        setPage(next);
      }
    }
    window.addEventListener("keydown", shortcut);
    return () => window.removeEventListener("keydown", shortcut);
  }, [canRunCustomReports, canRunReports]);

  async function transition(
    batchId: string,
    action: "validate" | "approve" | "post",
  ) {
    setBusyAction(`${batchId}:${action}`);
    setError("");
    try {
      await api(
        `/journals/${batchId}/${action}`,
        { method: "POST" },
        token,
        companyId,
      );
      await refresh();
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Workflow action failed",
      );
    } finally {
      setBusyAction("");
    }
  }

  async function reverse(entryId: string, reason: string) {
    const period = periods.find((item) => item.status === "open");
    if (!period) {
      setError("No open fiscal period is available for the reversal.");
      return;
    }
    setBusyAction(`reverse:${entryId}`);
    setError("");
    try {
      await api(
        `/journals/entries/${entryId}/reverse`,
        {
          method: "POST",
          body: JSON.stringify({
            posting_date: period.start_date,
            fiscal_period_id: period.id,
            reason,
          }),
        },
        token,
        companyId,
      );
      await refresh();
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Reversal could not be posted",
      );
    } finally {
      setBusyAction("");
    }
  }

  async function runIntegrity() {
    setBusyAction("integrity");
    setError("");
    try {
      const result = await api<{ ok: boolean }>(
        "/ledger/integrity",
        { method: "POST" },
        token,
        companyId,
      );
      setIntegrityResult(
        result.ok
          ? "Ledger and period balances reconcile."
          : "Integrity exceptions require review.",
      );
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Integrity check failed",
      );
    } finally {
      setBusyAction("");
    }
  }

  async function bulk(ids: string[], action: "validate" | "approve" | "post") {
    setBusyAction(`bulk:${action}`);
    setError("");
    setNotice(null);
    try {
      const result = await api<{
        succeeded: string[];
        failed: { detail: string }[];
      }>(
        "/journals/bulk",
        { method: "POST", body: JSON.stringify({ batch_ids: ids, action }) },
        token,
        companyId,
      );
      await refresh();
      if (result.failed.length)
        setNotice({
          tone: "warning",
          title: "Bulk action partially completed",
          message: `${result.succeeded.length} succeeded; ${result.failed.length} failed: ${result.failed[0].detail}`,
        });
      else
        setNotice({
          tone: "success",
          title: "Bulk action completed",
          message: `${result.succeeded.length} batches ${action}d successfully.`,
        });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Bulk action failed");
    } finally {
      setBusyAction("");
    }
  }

  async function updateDraft(batch: JournalBatch, description: string) {
    setBusyAction(`${batch.id}:update`);
    setError("");
    try {
      await api(
        `/journals/${batch.id}`,
        {
          method: "PUT",
          body: JSON.stringify({
            description,
            entries: batch.entries.map((entry) => ({
              entry_date: entry.entry_date,
              posting_date: entry.posting_date,
              fiscal_period_id: entry.fiscal_period_id,
              reference: entry.reference,
              description,
              lines: entry.lines.map((line) => ({
                account_id: line.account_id,
                description: line.description,
                currency_code: line.currency_code,
                exchange_rate: line.exchange_rate,
                debit: line.debit_original,
                credit: line.credit_original,
              })),
            })),
          }),
        },
        token,
        companyId,
      );
      await refresh();
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Draft could not be updated",
      );
    } finally {
      setBusyAction("");
    }
  }

  async function copyDraft(batchId: string) {
    setBusyAction(`${batchId}:copy`);
    setError("");
    try {
      await api(
        `/journals/${batchId}/copy`,
        { method: "POST" },
        token,
        companyId,
      );
      await refresh();
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Batch could not be copied",
      );
    } finally {
      setBusyAction("");
    }
  }

  async function deleteDraft(batchId: string) {
    setBusyAction(`${batchId}:delete`);
    setError("");
    try {
      await api(`/journals/${batchId}`, { method: "DELETE" }, token, companyId);
      await refresh();
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Draft could not be deleted",
      );
    } finally {
      setBusyAction("");
    }
  }

  if (!company)
    return (
      <main className="empty">
        <EmptyState
          kind="no-access"
          title="No company access"
          description="Your account has no active company membership."
          action={<Button onClick={onLogout}>Sign out</Button>}
        />
      </main>
    );

  return (
    <div className="app-shell">
      <SidebarNav
        groups={navGroups}
        activeId={page}
        onNavigate={(destination) => {
          setError("");
          setNotice(null);
          setPage(destination as Page);
        }}
        footer={
          <div className="identity">
            <span>{me.display_name.slice(0, 2).toUpperCase()}</span>
            <div>
              <strong>{me.display_name}</strong>
              <small>{company.role}</small>
            </div>
          </div>
        }
      />
      <header className="product-bar">
        <div className="product-wordmark">
          <span>CT</span>
          <strong>CTec Ledger</strong>
        </div>
        <div className="product-context">
          <CompanySwitcher
            company={company.name}
            code={company.code}
            role={company.role}
            memberships={me.companies.map((item) => ({
              id: item.id,
              company: item.name,
              code: item.code,
              role: item.role,
            }))}
            onSelect={(membership) => {
              if (!membership.id || membership.id === companyId) return;
              setPage("overview");
              setIntegrityResult("");
              setError("");
              setAccounts([]);
              setPeriods([]);
              setYears([]);
              setBatches([]);
              setBudgets([]);
              setReportRuns([]);
              setCompanyId(membership.id);
            }}
          />
          <div className="topbar-identity">
            <span>{me.display_name.slice(0, 2).toUpperCase()}</span>
            <div>
              <strong>{me.display_name}</strong>
              <small>{company.role}</small>
            </div>
          </div>
          <Button
            variant="ghost"
            className="topbar-signout"
            icon="log-out"
            onClick={onLogout}
          >
            Sign out
          </Button>
        </div>
      </header>
      <main className="workspace" key={company.id}>
        <PageHeader
          eyebrow={company.name}
          title={PAGE_TITLES[page]}
          meta={`${company.code} · ${company.role} · ${company.base_currency_code}`}
          dataState={dataState}
          actions={
            <Button
              variant="secondary"
              icon="refresh-cw"
              busy={dataState === "refreshing"}
              onClick={() => void refresh()}
            >
              Refresh
            </Button>
          }
        />
        <h2 className="ds-visually-hidden">{company.name}</h2>
        {error ? (
          <Banner tone="danger" title="Workspace action did not complete">
            {error}
          </Banner>
        ) : null}
        {notice ? (
          <Banner tone={notice.tone} title={notice.title}>
            {notice.message}
          </Banner>
        ) : null}
        {page === "overview" ? (
          <>
            <section className="hero-card">
              <div>
                <p className="eyebrow">CONTROLLED BOOKS</p>
                <h2>
                  {batches.filter((batch) => batch.status === "posted").length}{" "}
                  posted batches
                </h2>
                <p>
                  Current company context: <strong>{company.code}</strong>.
                  Every view and mutation is isolated by server-side membership.
                </p>
                {integrityResult ? (
                  <p role="status">{integrityResult}</p>
                ) : null}
              </div>
              <div className="hero-actions">
                <Button variant="primary" onClick={() => setPage("journals")}>
                  Open journal workspace
                </Button>
                {capabilities.has("integrity.run") ? (
                  <Button
                    busy={busyAction === "integrity"}
                    onClick={() => void runIntegrity()}
                  >
                    Run integrity
                  </Button>
                ) : null}
              </div>
            </section>
            <section className="metric-grid">
              <article>
                <span>Chart</span>
                <strong>{accounts.length}</strong>
                <small>normalized accounts</small>
              </article>
              <article>
                <span>Calendar</span>
                <strong>{periods.length}</strong>
                <small>configured periods</small>
              </article>
              <article>
                <span>Pending</span>
                <strong>
                  {batches.filter((batch) => batch.status !== "posted").length}
                </strong>
                <small>batches in workflow</small>
              </article>
            </section>
            <section className="panel">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">RECENT ACTIVITY</p>
                  <h2>Journal batches</h2>
                </div>
                <Button
                  variant="ghost"
                  icon="refresh-cw"
                  onClick={() => void refresh()}
                >
                  Refresh
                </Button>
              </div>
              <BatchList
                batches={batches.slice(0, 5)}
                capabilities={capabilities}
                busyAction={busyAction}
                onTransition={transition}
                onBulk={bulk}
                onUpdate={updateDraft}
                onCopy={copyDraft}
                onDelete={deleteDraft}
              />
            </section>
          </>
        ) : null}
        {page === "accounts" ? (
          <AccountManager
            accounts={accounts}
            company={company}
            capabilities={capabilities}
            token={token}
            onChanged={refresh}
          />
        ) : null}
        {page === "journals" ? (
          <div className="journal-layout">
            {capabilities.has("journals.create") ? (
              <JournalComposer
                accounts={accounts}
                periods={periods}
                onCreated={refresh}
                token={token}
                companyId={companyId}
              />
            ) : null}
            <section className="panel">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">WORKFLOW</p>
                  <h2>Journal batches</h2>
                </div>
                <Button
                  variant="ghost"
                  icon="refresh-cw"
                  onClick={() => void refresh()}
                >
                  Refresh
                </Button>
              </div>
              <BatchList
                batches={batches}
                capabilities={capabilities}
                busyAction={busyAction}
                onTransition={transition}
                onBulk={bulk}
                onUpdate={updateDraft}
                onCopy={copyDraft}
                onDelete={deleteDraft}
              />
            </section>
          </div>
        ) : null}
        {page === "inquiry" ? (
          <InquiryPanel
            entries={postedEntries}
            accounts={accounts}
            canReverse={capabilities.has("journals.reverse")}
            busy={busyAction.startsWith("reverse:")}
            onReverse={reverse}
          />
        ) : null}
        {page === "fiscal" ? (
          <FiscalCalendarManager
            token={token}
            company={company}
            years={years}
            periods={periods}
            canManage={capabilities.has("fiscal.manage")}
            onChanged={refresh}
          />
        ) : null}
        {page === "planning" ? (
          <PlanningPanel
            token={token}
            company={company}
            accounts={accounts}
            periods={periods}
            years={years}
            budgets={budgets}
            canBudget={canManageBudgets}
            canClose={capabilities.has("fiscal.close")}
            onChanged={refresh}
          />
        ) : null}
        {page === "reports" ? (
          <ReportPanel
            token={token}
            company={company}
            periods={periods}
            runs={reportRuns}
            onChanged={refresh}
          />
        ) : null}
        {page === "designer" ? (
          <CustomReportDesigner
            key={company.id}
            token={token}
            company={company}
            periods={periods}
            canDesign={capabilities.has("reports.custom.design")}
          />
        ) : null}
        {page === "admin" ? (
          <AdminPanel
            token={token}
            company={company}
            capabilities={capabilities}
            periods={periods}
          />
        ) : null}
      </main>
    </div>
  );
}

type BatchListProps = {
  batches: JournalBatch[];
  capabilities: Set<string>;
  busyAction: string;
  onTransition: (
    id: string,
    action: "validate" | "approve" | "post",
  ) => Promise<void>;
  onBulk: (
    ids: string[],
    action: "validate" | "approve" | "post",
  ) => Promise<void>;
  onUpdate: (batch: JournalBatch, description: string) => Promise<void>;
  onCopy: (id: string) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
};

function DraftActions({
  batch,
  capabilities,
  busy,
  onUpdate,
  onCopy,
  onDelete,
}: {
  batch: JournalBatch;
  capabilities: Set<string>;
  busy: boolean;
  onUpdate: BatchListProps["onUpdate"];
  onCopy: BatchListProps["onCopy"];
  onDelete: BatchListProps["onDelete"];
}) {
  const [description, setDescription] = useState(batch.description);
  const [confirmDelete, setConfirmDelete] = useState(false);
  return (
    <div className="draft-actions">
      {capabilities.has("journals.update") ? (
        <>
          <Input
            aria-label={`Draft description for ${batch.batch_no}`}
            value={description}
            onChange={(event) => setDescription(event.target.value)}
          />
          <Button
            size="sm"
            disabled={
              busy || !description.trim() || description === batch.description
            }
            onClick={() => void onUpdate(batch, description)}
          >
            Save draft
          </Button>
        </>
      ) : null}
      {capabilities.has("journals.create") ? (
        <Button
          size="sm"
          icon="copy"
          disabled={busy}
          onClick={() => void onCopy(batch.id)}
        >
          Copy
        </Button>
      ) : null}
      {capabilities.has("journals.delete") ? (
        <Button
          size="sm"
          variant="danger"
          disabled={busy}
          onClick={() => setConfirmDelete(true)}
        >
          Delete draft
        </Button>
      ) : null}
      <Dialog
        open={confirmDelete}
        tone="danger"
        title="Delete draft journal"
        subject={batch.batch_no}
        consequence="This removes the unposted draft only. No posted ledger entry or audit history is changed."
        confirmLabel="Delete draft"
        busy={busy}
        onCancel={() => setConfirmDelete(false)}
        onConfirm={() =>
          void onDelete(batch.id).then(() => setConfirmDelete(false))
        }
      />
    </div>
  );
}

function BatchList({
  batches,
  capabilities,
  busyAction,
  onTransition,
  onBulk,
  onUpdate,
  onCopy,
  onDelete,
}: BatchListProps) {
  const [selected, setSelected] = useState<Set<string>>(() => new Set());
  const [pendingPost, setPendingPost] = useState<{
    ids: string[];
    subject: string;
    bulk: boolean;
  } | null>(null);
  if (!batches.length)
    return (
      <EmptyState
        title="No journal batches yet"
        description="Create a balanced draft when this company is ready to record activity."
      />
    );
  const ids = [...selected];
  function toggle(id: string) {
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }
  return (
    <>
      <div className="bulk-bar">
        <span>{selected.size} marked</span>
        {capabilities.has("journals.validate") ? (
          <Button
            size="sm"
            disabled={!selected.size || Boolean(busyAction)}
            onClick={() =>
              void onBulk(ids, "validate").then(() => setSelected(new Set()))
            }
          >
            Bulk validate
          </Button>
        ) : null}
        {capabilities.has("journals.approve") ? (
          <Button
            size="sm"
            disabled={!selected.size || Boolean(busyAction)}
            onClick={() =>
              void onBulk(ids, "approve").then(() => setSelected(new Set()))
            }
          >
            Bulk approve
          </Button>
        ) : null}
        {capabilities.has("journals.post") ? (
          <Button
            size="sm"
            variant="primary"
            disabled={!selected.size || Boolean(busyAction)}
            onClick={() =>
              setPendingPost({
                ids,
                subject: `${ids.length} approved batches`,
                bulk: true,
              })
            }
          >
            Bulk post
          </Button>
        ) : null}
      </div>
      <div className="batch-list">
        {batches.map((batch) => (
          <article className="batch" key={batch.id}>
            <Checkbox
              checked={selected.has(batch.id)}
              onChange={() => toggle(batch.id)}
              aria-label={`Mark ${batch.batch_no}`}
            />
            <div>
              <StatusPill status={batch.status as LedgerStatus} />
              <h3>{batch.batch_no}</h3>
              <p>{batch.description || batch.entries[0]?.description}</p>
              <small>
                {batch.entries.length}{" "}
                {batch.entries.length === 1 ? "entry" : "entries"} ·{" "}
                {new Date(batch.created_at).toLocaleDateString()}
              </small>
              {batch.status === "draft" ? (
                <DraftActions
                  batch={batch}
                  capabilities={capabilities}
                  busy={Boolean(busyAction)}
                  onUpdate={onUpdate}
                  onCopy={onCopy}
                  onDelete={onDelete}
                />
              ) : null}
            </div>
            <div className="batch-actions">
              {batch.status === "draft" &&
              capabilities.has("journals.validate") ? (
                <Button
                  size="sm"
                  disabled={Boolean(busyAction)}
                  onClick={() => void onTransition(batch.id, "validate")}
                >
                  Validate
                </Button>
              ) : null}
              {batch.status === "validated" &&
              capabilities.has("journals.approve") ? (
                <Button
                  size="sm"
                  disabled={Boolean(busyAction)}
                  onClick={() => void onTransition(batch.id, "approve")}
                >
                  Approve
                </Button>
              ) : null}
              {batch.status === "approved" &&
              capabilities.has("journals.post") ? (
                <Button
                  size="sm"
                  variant="primary"
                  disabled={Boolean(busyAction)}
                  onClick={() =>
                    setPendingPost({
                      ids: [batch.id],
                      subject: batch.batch_no,
                      bulk: false,
                    })
                  }
                >
                  Post
                </Button>
              ) : null}
            </div>
          </article>
        ))}
      </div>
      <Dialog
        open={Boolean(pendingPost)}
        tone="danger"
        title={
          pendingPost?.bulk
            ? "Post approved journal batches"
            : "Post approved journal batch"
        }
        subject={pendingPost?.subject}
        consequence="Posting writes immutable journal and ledger history. Corrections must be recorded as new linked reversals."
        confirmLabel={pendingPost?.bulk ? "Post batches" : "Post batch"}
        busy={Boolean(busyAction)}
        onCancel={() => setPendingPost(null)}
        onConfirm={() => {
          if (!pendingPost) return;
          const action = pendingPost.bulk
            ? onBulk(pendingPost.ids, "post")
            : onTransition(pendingPost.ids[0], "post");
          void action.then(() => {
            setSelected(new Set());
            setPendingPost(null);
          });
        }}
      />
    </>
  );
}

type AdminProps = {
  token: string;
  company: CompanyAccess;
  capabilities: Set<string>;
  periods: Period[];
};
type ImportPreview = {
  source_digest: string;
  rows: number;
  valid?: number;
  entries?: number;
  errors: { row: number; message: string }[];
};

function ImportCard({
  kind,
  token,
  companyId,
  onApplied,
}: {
  kind: "accounts" | "journals";
  token: string;
  companyId: string;
  onApplied: () => Promise<void>;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  async function execute(action: "preview" | "apply") {
    if (!file) return;
    setBusy(true);
    setMessage("");
    try {
      const result = await apiUpload<
        ImportPreview & {
          created?: number;
          updated?: number;
          batch_id?: string;
        }
      >(`/imports/${kind}/${action}`, file, token, companyId);
      if (action === "preview") {
        setPreview(result);
        setMessage(
          result.errors.length
            ? "Preview contains validation exceptions."
            : "Preview is valid and ready to apply.",
        );
      } else {
        setPreview(null);
        setMessage(
          kind === "accounts"
            ? `${result.created ?? 0} accounts created; ${result.updated ?? 0} updated.`
            : `Journal batch ${result.batch_id ?? "created"} imported as a draft.`,
        );
        await onApplied();
      }
    } catch (caught) {
      setMessage(caught instanceof Error ? caught.message : "Import failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <article className="import-card">
      <div>
        <p className="eyebrow">CONTROLLED CSV</p>
        <h3>{kind === "accounts" ? "Account import" : "Journal import"}</h3>
      </div>
      <Field
        label={kind === "accounts" ? "Account CSV" : "Journal CSV"}
        htmlFor={`${kind}-csv`}
      >
        <Input
          type="file"
          accept=".csv,text/csv"
          onChange={(event) => {
            setFile(event.target.files?.[0] ?? null);
            setPreview(null);
            setMessage("");
          }}
        />
      </Field>
      <div className="button-row">
        <Button
          disabled={!file || busy}
          onClick={() => void execute("preview")}
        >
          Preview
        </Button>
        <Button
          variant="primary"
          disabled={!file || busy || !preview || preview.errors.length > 0}
          onClick={() => void execute("apply")}
        >
          Apply validated file
        </Button>
      </div>
      {preview ? (
        <dl className="import-summary">
          <div>
            <dt>Rows</dt>
            <dd>{preview.rows}</dd>
          </div>
          <div>
            <dt>Valid</dt>
            <dd>{preview.valid ?? preview.entries ?? 0}</dd>
          </div>
          <div>
            <dt>Exceptions</dt>
            <dd>{preview.errors.length}</dd>
          </div>
        </dl>
      ) : null}
      {preview?.errors.map((item) => (
        <Banner tone="danger" key={`${item.row}-${item.message}`}>
          Row {item.row}: {item.message}
        </Banner>
      ))}
      {message ? (
        <Banner
          tone={
            message.includes("failed")
              ? "danger"
              : preview?.errors.length
                ? "warning"
                : "success"
          }
        >
          {message}
        </Banner>
      ) : null}
    </article>
  );
}

function MembershipRow({
  membership,
  roles,
  disabled,
  onSave,
}: {
  membership: AdminMembership;
  roles: AdminRole[];
  disabled: boolean;
  onSave: (userId: string, roleId: string, active: boolean) => Promise<void>;
}) {
  const [roleId, setRoleId] = useState(membership.role_id);
  const [active, setActive] = useState(membership.active);
  const changed = roleId !== membership.role_id || active !== membership.active;
  return (
    <tr>
      <td>{membership.display_name}</td>
      <td>{membership.email}</td>
      <td>
        <Select
          aria-label={`Role for ${membership.email}`}
          value={roleId}
          onChange={(event) => setRoleId(event.target.value)}
        >
          {roles.map((role) => (
            <option key={role.id} value={role.id}>
              {role.name}
            </option>
          ))}
        </Select>
      </td>
      <td>
        <Checkbox
          className="membership-active"
          label="Active"
          checked={active}
          onChange={(event) => setActive(event.target.checked)}
        />
      </td>
      <td>
        <Button
          size="sm"
          disabled={disabled || !changed}
          onClick={() => void onSave(membership.user_id, roleId, active)}
        >
          Save
        </Button>
      </td>
    </tr>
  );
}

function AdminPanel({ token, company, capabilities, periods }: AdminProps) {
  const [memberships, setMemberships] = useState<AdminMembership[]>([]);
  const [roles, setRoles] = useState<AdminRole[]>([]);
  const [audit, setAudit] = useState<AuditEvent[]>([]);
  const [operations, setOperations] = useState<Operation[]>([]);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [roleName, setRoleName] = useState("Read-only analyst");
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [roleId, setRoleId] = useState("");
  const [density, setDensity] = useState("comfortable");
  const canUsers = capabilities.has("users.manage");
  const canAudit = capabilities.has("audit.view");
  const canPreferences = capabilities.has("preferences.manage");
  const canJobs = capabilities.has("administration.organize");

  const refresh = useCallback(async () => {
    const [nextUsers, nextRoles, nextAudit, nextOperations] = await Promise.all(
      [
        canUsers
          ? api<AdminMembership[]>(
              "/administration/users",
              {},
              token,
              company.id,
            )
          : Promise.resolve([]),
        canUsers
          ? api<AdminRole[]>("/administration/roles", {}, token, company.id)
          : Promise.resolve([]),
        canAudit
          ? api<AuditEvent[]>(
              "/administration/audit?limit=50",
              {},
              token,
              company.id,
            )
          : Promise.resolve([]),
        canAudit
          ? api<Operation[]>(
              "/administration/operations",
              {},
              token,
              company.id,
            )
          : Promise.resolve([]),
      ],
    );
    setMemberships(nextUsers);
    setRoles(nextRoles);
    setAudit(nextAudit);
    setOperations(nextOperations);
  }, [canAudit, canUsers, company.id, token]);

  useEffect(() => {
    const handle = window.setTimeout(() => {
      void refresh().catch((caught: unknown) =>
        setMessage(
          caught instanceof Error
            ? caught.message
            : "Administration data could not be loaded",
        ),
      );
    }, 0);
    return () => window.clearTimeout(handle);
  }, [refresh]);

  async function createRole(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      const role = await api<AdminRole>(
        "/administration/roles",
        {
          method: "POST",
          body: JSON.stringify({
            name: roleName,
            permissions: [
              "accounts.view",
              "fiscal.view",
              "reports.run",
              "preferences.manage",
            ],
          }),
        },
        token,
        company.id,
      );
      setRoleId(role.id);
      setMessage(
        `Role ${role.name} created with least-privilege reporting access.`,
      );
      await refresh();
    } catch (caught) {
      setMessage(
        caught instanceof Error ? caught.message : "Role could not be created",
      );
    } finally {
      setBusy(false);
    }
  }

  async function createUser(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      await api(
        "/administration/users",
        {
          method: "POST",
          body: JSON.stringify({
            email,
            display_name: displayName,
            password,
            role_id: roleId || roles[0]?.id,
          }),
        },
        token,
        company.id,
      );
      setEmail("");
      setDisplayName("");
      setPassword("");
      setMessage("Company membership created and recorded in the audit trail.");
      await refresh();
    } catch (caught) {
      setMessage(
        caught instanceof Error ? caught.message : "User could not be added",
      );
    } finally {
      setBusy(false);
    }
  }

  async function updateMembership(
    userId: string,
    nextRoleId: string,
    active: boolean,
  ) {
    setBusy(true);
    setMessage("");
    try {
      await api(
        `/administration/users/${userId}`,
        {
          method: "PUT",
          body: JSON.stringify({ role_id: nextRoleId, active }),
        },
        token,
        company.id,
      );
      setMessage("Membership role and status updated with audit evidence.");
      await refresh();
    } catch (caught) {
      setMessage(
        caught instanceof Error
          ? caught.message
          : "Membership could not be updated",
      );
    } finally {
      setBusy(false);
    }
  }

  async function savePreference() {
    setBusy(true);
    setMessage("");
    try {
      await api(
        "/administration/preferences/display",
        {
          method: "PUT",
          body: JSON.stringify({
            value: { density, date_format: "YYYY-MM-DD" },
          }),
        },
        token,
        company.id,
      );
      setMessage("Display preference saved for this user and company.");
    } catch (caught) {
      setMessage(
        caught instanceof Error
          ? caught.message
          : "Preference could not be saved",
      );
    } finally {
      setBusy(false);
    }
  }

  async function saveView() {
    setBusy(true);
    setMessage("");
    try {
      await api(
        "/administration/saved-views",
        {
          method: "POST",
          body: JSON.stringify({
            resource: "general_ledger",
            name: "Current-period activity",
            definition: { include_zero: false },
            shared: false,
          }),
        },
        token,
        company.id,
      );
      setMessage("Saved view created for the current user and company.");
    } catch (caught) {
      setMessage(
        caught instanceof Error
          ? caught.message
          : "Saved view could not be created",
      );
    } finally {
      setBusy(false);
    }
  }

  async function startJob(kind: "integrity" | "trial_balance") {
    setBusy(true);
    setMessage("");
    try {
      const parameters =
        kind === "trial_balance"
          ? {
              period_id: periods[0]?.id,
              include_zero: false,
              include_titles: true,
            }
          : {};
      const started = await api<Operation>(
        "/administration/operations",
        { method: "POST", body: JSON.stringify({ kind, parameters }) },
        token,
        company.id,
      );
      setMessage(`${kind.replaceAll("_", " ")} operation started.`);
      for (let attempt = 0; attempt < 20; attempt += 1) {
        await new Promise((resolve) => window.setTimeout(resolve, 250));
        const latest = await api<Operation[]>(
          "/administration/operations",
          {},
          token,
          company.id,
        );
        setOperations(latest);
        const current = latest.find((item) => item.id === started.id);
        if (current?.status === "succeeded" || current?.status === "failed") {
          setMessage(
            current.status === "succeeded"
              ? `${kind.replaceAll("_", " ")} operation completed.`
              : `${kind.replaceAll("_", " ")} operation failed: ${current.error ?? "unknown error"}`,
          );
          await refresh();
          return;
        }
      }
      setMessage(
        `${kind.replaceAll("_", " ")} operation is still running; refresh history for its final status.`,
      );
    } catch (caught) {
      setMessage(
        caught instanceof Error
          ? caught.message
          : "Operation could not be started",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="admin-layout">
      <section className="panel admin-intro">
        <div className="section-heading">
          <div>
            <p className="eyebrow">COMPANY CONTROLS</p>
            <h2>Administration</h2>
          </div>
          <Badge tone="success">Capability secured</Badge>
        </div>
        <p>
          Imports are previewed before atomic application. Membership,
          preferences, jobs, and audit evidence remain scoped to{" "}
          <strong>{company.code}</strong>.
        </p>
        {message ? (
          <Banner
            tone={
              message.includes("failed") || message.includes("could not")
                ? "danger"
                : "success"
            }
          >
            {message}
          </Banner>
        ) : null}
      </section>
      <AdministrationSettings
        token={token}
        company={company}
        capabilities={capabilities}
      />
      {capabilities.has("accounts.import") ? (
        <ImportCard
          kind="accounts"
          token={token}
          companyId={company.id}
          onApplied={refresh}
        />
      ) : null}
      {capabilities.has("journals.import") ? (
        <ImportCard
          kind="journals"
          token={token}
          companyId={company.id}
          onApplied={refresh}
        />
      ) : null}
      {capabilities.has("migration.run") ? (
        <LegacyMigrationPanel token={token} company={company} />
      ) : null}
      {canUsers ? (
        <section className="panel admin-users">
          <div className="section-heading">
            <div>
              <p className="eyebrow">LEAST PRIVILEGE</p>
              <h2>Users and roles</h2>
            </div>
            <Badge>{memberships.length} members</Badge>
          </div>
          <div className="admin-forms">
            <form onSubmit={createRole}>
              <h3>Create reporting role</h3>
              <Field label="Role name" htmlFor="admin-role-name">
                <Input
                  value={roleName}
                  onChange={(event) => setRoleName(event.target.value)}
                  required
                />
              </Field>
              <Button type="submit" busy={busy}>
                Create role
              </Button>
            </form>
            <form onSubmit={createUser}>
              <h3>Add company user</h3>
              <Field label="Email" htmlFor="admin-user-email">
                <Input
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  required
                />
              </Field>
              <Field label="Display name" htmlFor="admin-user-display-name">
                <Input
                  value={displayName}
                  onChange={(event) => setDisplayName(event.target.value)}
                  required
                />
              </Field>
              <Field label="Temporary password" htmlFor="admin-user-password">
                <Input
                  type="password"
                  minLength={12}
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  required
                />
              </Field>
              <Field label="Role" htmlFor="admin-user-role">
                <Select
                  value={roleId || roles[0]?.id || ""}
                  onChange={(event) => setRoleId(event.target.value)}
                >
                  {roles.map((role) => (
                    <option key={role.id} value={role.id}>
                      {role.name}
                    </option>
                  ))}
                </Select>
              </Field>
              <Button
                type="submit"
                variant="primary"
                busy={busy}
                disabled={!roles.length}
              >
                Add user
              </Button>
            </form>
          </div>
          <div className="table-wrap">
            <table>
              <caption className="ds-visually-hidden">
                Company memberships and assigned roles
              </caption>
              <thead>
                <tr>
                  <th>User</th>
                  <th>Email</th>
                  <th>Role</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {memberships.map((item) => (
                  <MembershipRow
                    key={`${item.user_id}:${item.role_id}:${item.active}`}
                    membership={item}
                    roles={roles}
                    disabled={busy}
                    onSave={updateMembership}
                  />
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}
      {canPreferences ? (
        <section className="panel preference-card">
          <div>
            <p className="eyebrow">PRACTICAL PERSONALIZATION</p>
            <h2>Views and display</h2>
          </div>
          <Field label="Density" htmlFor="admin-density">
            <Select
              value={density}
              onChange={(event) => setDensity(event.target.value)}
            >
              <option value="comfortable">Comfortable</option>
              <option value="compact">Compact</option>
            </Select>
          </Field>
          <div className="button-row">
            <Button disabled={busy} onClick={() => void savePreference()}>
              Save display
            </Button>
            <Button disabled={busy} onClick={() => void saveView()}>
              Save ledger view
            </Button>
          </div>
        </section>
      ) : null}
      {canJobs ? (
        <section className="panel operation-card">
          <div>
            <p className="eyebrow">BACKGROUND CONTROL</p>
            <h2>Operations</h2>
          </div>
          <div className="button-row">
            <Button disabled={busy} onClick={() => void startJob("integrity")}>
              Run integrity job
            </Button>
            <Button
              disabled={busy || !periods.length}
              onClick={() => void startJob("trial_balance")}
            >
              Build trial balance
            </Button>
          </div>
          {operations.slice(0, 8).map((item) => (
            <ProgressBar
              key={item.id}
              label={item.kind.replaceAll("_", " ")}
              status={
                item.status as Extract<
                  LedgerStatus,
                  "queued" | "running" | "succeeded" | "failed"
                >
              }
              value={item.progress}
            />
          ))}
          {operations.some(
            (item) => item.status === "queued" || item.status === "running",
          ) ? (
            <p className="muted">
              Jobs continue on the server when you navigate away.
            </p>
          ) : null}
        </section>
      ) : null}
      {canAudit ? (
        <section className="panel audit-card">
          <div className="section-heading">
            <div>
              <p className="eyebrow">IMMUTABLE EVIDENCE</p>
              <h2>Audit history</h2>
            </div>
            <Button icon="refresh-cw" onClick={() => void refresh()}>
              Refresh
            </Button>
          </div>
          <div className="audit-list">
            {audit.map((event) => (
              <article key={event.id}>
                <strong>{event.action.replaceAll(".", " · ")}</strong>
                <span>
                  {event.entity_type} · {event.entity_id}
                </span>
                <time dateTime={event.occurred_at}>
                  {new Date(event.occurred_at).toLocaleString()}
                </time>
              </article>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}

type InquiryProps = {
  entries: JournalEntry[];
  accounts: Account[];
  canReverse: boolean;
  busy: boolean;
  onReverse: (entryId: string, reason: string) => Promise<void>;
};

function InquiryPanel({
  entries,
  accounts,
  canReverse,
  busy,
  onReverse,
}: InquiryProps) {
  const [selected, setSelected] = useState("");
  const [reason, setReason] = useState("Correction requested after review");
  const accountNames = useMemo(
    () =>
      new Map(
        accounts.map((account) => [
          account.id,
          `${account.code} · ${account.name}`,
        ]),
      ),
    [accounts],
  );
  const selectedEntry = entries.find((entry) => entry.id === selected);
  return (
    <section className="panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">IMMUTABLE DETAIL</p>
          <h2>Posted journal inquiry</h2>
        </div>
        <Badge tone="success">{entries.length} entries</Badge>
      </div>
      <Banner live="off" tone="info" title="Posted entries are immutable">
        <span>
          <Icon name="lock" size={12} /> Corrections are recorded as new linked
          reversals; the original entry remains unchanged.
        </span>
      </Banner>
      <Dialog
        open={Boolean(selectedEntry)}
        tone="danger"
        title="Post linked reversal"
        subject={selectedEntry?.entry_no}
        consequence="A new reversing journal will be posted in the selected open fiscal period. The original posted entry remains immutable."
        confirmLabel="Post linked reversal"
        busy={busy}
        onCancel={() => setSelected("")}
        onConfirm={() => {
          if (selectedEntry && reason.trim().length >= 3)
            void onReverse(selectedEntry.id, reason).then(() =>
              setSelected(""),
            );
        }}
      >
        <Field
          label="Reversal reason"
          htmlFor="reversal-reason"
          required
          hint="This reason becomes part of the audit evidence."
        >
          <Input
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            minLength={3}
            required
          />
        </Field>
      </Dialog>
      <div className="batch-list">
        {entries.map((entry) => (
          <article className="entry-detail" key={entry.id}>
            <div className="section-heading">
              <div>
                <StatusPill
                  status={entry.reversal_of_id ? "reversed" : "posted"}
                />
                <h3>
                  {entry.entry_no} · {entry.description}
                </h3>
                <small>
                  {entry.posting_date}
                  {entry.reversal_of_id ? " · reversing entry" : ""}
                </small>
              </div>
              {canReverse && !entry.reversal_of_id ? (
                <Button onClick={() => setSelected(entry.id)} icon="undo-2">
                  Reverse
                </Button>
              ) : null}
            </div>
            <table>
              <caption className="ds-visually-hidden">
                Debit and credit lines for {entry.entry_no}
              </caption>
              <thead>
                <tr>
                  <th>Account</th>
                  <th>Debit</th>
                  <th>Credit</th>
                </tr>
              </thead>
              <tbody>
                {entry.lines.map((line) => (
                  <tr key={line.id}>
                    <td>
                      {accountNames.get(line.account_id) ?? line.account_id}
                    </td>
                    <td>
                      <AmountCell
                        value={line.debit_base}
                        side="debit"
                        currency={line.currency_code}
                      />
                    </td>
                    <td>
                      <AmountCell
                        value={line.credit_base}
                        side="credit"
                        currency={line.currency_code}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </article>
        ))}
      </div>
    </section>
  );
}

type PlanningProps = {
  token: string;
  company: CompanyAccess;
  accounts: Account[];
  periods: Period[];
  years: FiscalYear[];
  budgets: Budget[];
  canBudget: boolean;
  canClose: boolean;
  onChanged: () => Promise<void>;
};

function PlanningPanel({
  token,
  company,
  accounts,
  periods,
  years,
  budgets,
  canBudget,
  canClose,
  onChanged,
}: PlanningProps) {
  const postable = accounts.filter(
    (account) => account.active && account.postable,
  );
  const [scenario, setScenario] = useState("Current");
  const [amount, setAmount] = useState("0.00");
  const [accountId, setAccountId] = useState("");
  const [periodId, setPeriodId] = useState("");
  const [yearId, setYearId] = useState("");
  const [openingPeriodId, setOpeningPeriodId] = useState("");
  const [preview, setPreview] = useState<ClosePreview | null>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [confirmClose, setConfirmClose] = useState(false);
  const selectedAccount = accountId || postable[0]?.id || "";
  const selectedPeriod = periodId || periods[0]?.id || "";
  const openYear = years.find(
    (year) => year.id === (yearId || years.find((item) => !item.closed_at)?.id),
  );
  const openingCandidates = openYear
    ? periods.filter(
        (period) =>
          period.status === "open" && period.start_date > openYear.end_date,
      )
    : [];
  const selectedOpening = openingPeriodId || openingCandidates[0]?.id || "";

  async function saveBudget(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      await api(
        "/budgets",
        {
          method: "PUT",
          body: JSON.stringify({
            fiscal_period_id: selectedPeriod,
            account_id: selectedAccount,
            scenario,
            currency_code: company.base_currency_code,
            amount,
          }),
        },
        token,
        company.id,
      );
      setMessage("Budget version saved with audit history.");
      await onChanged();
    } catch (caught) {
      setMessage(
        caught instanceof Error ? caught.message : "Budget could not be saved",
      );
    } finally {
      setBusy(false);
    }
  }

  async function previewClose() {
    if (!openYear || !selectedOpening) return;
    setBusy(true);
    setMessage("");
    try {
      const result = await api<ClosePreview>(
        `/fiscal/years/${openYear.id}/close-preview`,
        {
          method: "POST",
          body: JSON.stringify({
            opening_period_id: selectedOpening,
            reason: "Approved fiscal-year close",
          }),
        },
        token,
        company.id,
      );
      setPreview(result);
      setMessage(
        result.balanced
          ? "Preview reconciles. Review the lines before execution."
          : "Preview does not reconcile.",
      );
    } catch (caught) {
      setMessage(
        caught instanceof Error ? caught.message : "Close preview failed",
      );
    } finally {
      setBusy(false);
    }
  }

  async function executeClose() {
    if (!openYear || !selectedOpening || !preview?.balanced) return;
    setBusy(true);
    setMessage("");
    try {
      await api(
        `/fiscal/years/${openYear.id}/close`,
        {
          method: "POST",
          body: JSON.stringify({
            opening_period_id: selectedOpening,
            reason: "Approved in reviewed browser preview",
          }),
        },
        token,
        company.id,
      );
      setPreview(null);
      setConfirmClose(false);
      setMessage(
        "Fiscal close posted. Historical periods remain immutable and closed.",
      );
      await onChanged();
    } catch (caught) {
      setMessage(
        caught instanceof Error ? caught.message : "Fiscal close failed",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="planning-grid">
      {canBudget ? (
        <section className="panel">
          <div className="section-heading">
            <div>
              <p className="eyebrow">VERSIONED PLANNING</p>
              <h2>Budgets</h2>
            </div>
            <Badge>{budgets.length} rows</Badge>
          </div>
          <form onSubmit={saveBudget}>
            <Field label="Scenario" htmlFor="budget-scenario" required>
              <Input
                value={scenario}
                onChange={(event) => setScenario(event.target.value)}
                required
              />
            </Field>
            <div className="form-grid">
              <Field label="Period" htmlFor="budget-period" required>
                <Select
                  value={selectedPeriod}
                  onChange={(event) => setPeriodId(event.target.value)}
                >
                  {periods.map((period) => (
                    <option key={period.id} value={period.id}>
                      {period.label}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label="Account" htmlFor="budget-account" required>
                <Select
                  value={selectedAccount}
                  onChange={(event) => setAccountId(event.target.value)}
                >
                  {postable.map((account) => (
                    <option key={account.id} value={account.id}>
                      {account.code} · {account.name}
                    </option>
                  ))}
                </Select>
              </Field>
            </div>
            <Field
              label={`Budget amount (${company.base_currency_code})`}
              htmlFor="budget-amount"
            >
              <Input
                numeric
                suffix={company.base_currency_code}
                inputMode="decimal"
                value={amount}
                onChange={(event) => setAmount(event.target.value)}
              />
            </Field>
            <Button
              type="submit"
              variant="primary"
              busy={busy}
              disabled={!selectedPeriod || !selectedAccount}
            >
              Save budget version
            </Button>
          </form>
          <div className="table-wrap">
            <table>
              <caption className="ds-visually-hidden">
                Versioned budget rows
              </caption>
              <thead>
                <tr>
                  <th>Scenario</th>
                  <th>Period</th>
                  <th>Account</th>
                  <th>Amount</th>
                </tr>
              </thead>
              <tbody>
                {budgets.map((budget) => (
                  <tr key={budget.id}>
                    <td>{budget.scenario}</td>
                    <td>
                      {
                        periods.find(
                          (period) => period.id === budget.fiscal_period_id,
                        )?.label
                      }
                    </td>
                    <td>
                      {
                        accounts.find(
                          (account) => account.id === budget.account_id,
                        )?.code
                      }
                    </td>
                    <td>
                      <AmountCell
                        value={budget.amount}
                        currency={budget.currency_code}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}
      {canClose ? (
        <section className="panel close-panel">
          <div className="section-heading">
            <div>
              <p className="eyebrow">APPEND-ONLY CONTROL</p>
              <h2>Fiscal close</h2>
            </div>
            <Badge tone="warning">Preview required</Badge>
          </div>
          <Field label="Fiscal year" htmlFor="close-year">
            <Select
              value={openYear?.id ?? ""}
              onChange={(event) => {
                setYearId(event.target.value);
                setOpeningPeriodId("");
                setPreview(null);
              }}
            >
              {years.map((year) => (
                <option
                  key={year.id}
                  value={year.id}
                  disabled={Boolean(year.closed_at)}
                >
                  {year.label}
                  {year.closed_at ? " · closed" : ""}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Opening period" htmlFor="close-opening-period">
            <Select
              value={selectedOpening}
              onChange={(event) => {
                setOpeningPeriodId(event.target.value);
                setPreview(null);
              }}
            >
              {openingCandidates.map((period) => (
                <option key={period.id} value={period.id}>
                  {period.label} · {period.start_date}
                </option>
              ))}
            </Select>
          </Field>
          <Button
            onClick={() => void previewClose()}
            busy={busy}
            disabled={!openYear || !selectedOpening}
          >
            Preview close
          </Button>
          {preview ? (
            <div className="close-preview">
              <StatusPill
                status={preview.balanced ? "reconciled" : "exception"}
              />
              <KeyValueList
                columns={3}
                items={[
                  {
                    label: "Profit / loss",
                    value: (
                      <AmountCell
                        value={preview.profit_loss}
                        currency={company.base_currency_code}
                      />
                    ),
                    numeric: true,
                  },
                  {
                    label: "Closing lines",
                    value: preview.closing_lines,
                    numeric: true,
                  },
                  {
                    label: "Opening lines",
                    value: preview.opening_lines,
                    numeric: true,
                  },
                ]}
              />
              <Button
                variant="primary"
                onClick={() => setConfirmClose(true)}
                disabled={busy || !preview.balanced}
              >
                Execute non-destructive close
              </Button>
            </div>
          ) : null}
          <Banner live="off" tone="info" title="Close is append-only">
            Closing posts immutable retained-earnings and opening entries. It
            never deletes or rewrites journals.
          </Banner>
          <Dialog
            open={confirmClose}
            title="Execute fiscal close"
            subject={`${openYear?.label ?? "Fiscal year"} · ${company.code}`}
            consequence="Closing and opening entries will be posted as immutable ledger history. Existing journals remain unchanged."
            confirmLabel="Execute close"
            busy={busy}
            onCancel={() => setConfirmClose(false)}
            onConfirm={() => void executeClose()}
          />
        </section>
      ) : null}
      {message ? (
        <Banner
          tone={
            /failed|error|locked|denied|unavailable|could not/i.test(message)
              ? "danger"
              : preview && !preview.balanced
                ? "warning"
                : "success"
          }
        >
          {message}
        </Banner>
      ) : null}
    </div>
  );
}

type ReportProps = {
  token: string;
  company: CompanyAccess;
  periods: Period[];
  runs: ReportRun[];
  onChanged: () => Promise<void>;
};

const REPORT_TYPES = [
  ["trial_balance", "Trial balance"],
  ["general_ledger", "General ledger listing"],
  ["chart_of_accounts", "Chart of accounts"],
  ["transaction_groups", "Transaction groups"],
  ["pre_post", "Pre-post journals"],
  ["close_history", "Closing history"],
  ["integrity", "Integrity report"],
] as const;

function ReportPanel({
  token,
  company,
  periods,
  runs,
  onChanged,
}: ReportProps) {
  const [reportType, setReportType] = useState("trial_balance");
  const [periodId, setPeriodId] = useState("");
  const [format, setFormat] = useState("json");
  const [result, setResult] = useState<ReportResult | null>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const selectedPeriod = periodId || periods[0]?.id || "";

  function parameters() {
    if (reportType === "trial_balance")
      return {
        period_id: selectedPeriod,
        include_zero: false,
        include_titles: true,
      };
    if (reportType === "general_ledger")
      return { from_period_id: selectedPeriod, to_period_id: selectedPeriod };
    return {};
  }

  async function run(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    setResult(null);
    const request = {
      report_type: reportType,
      parameters: parameters(),
      format,
    };
    try {
      if (format === "json") {
        setResult(
          await api<ReportResult>(
            "/reports/run",
            { method: "POST", body: JSON.stringify(request) },
            token,
            company.id,
          ),
        );
      } else {
        const downloaded = await apiDownload(
          "/reports/run",
          request,
          token,
          company.id,
        );
        const url = URL.createObjectURL(downloaded.blob);
        const anchor = document.createElement("a");
        anchor.href = url;
        anchor.download = downloaded.filename;
        anchor.click();
        URL.revokeObjectURL(url);
        setMessage(
          `${format.toUpperCase()} export generated from a saved report run.`,
        );
      }
      await onChanged();
    } catch (caught) {
      setMessage(caught instanceof Error ? caught.message : "Report failed");
    } finally {
      setBusy(false);
    }
  }

  async function reproduce(runId: string) {
    setBusy(true);
    setMessage("");
    try {
      setResult(
        await api<ReportResult>(
          `/reports/runs/${runId}/reproduce`,
          { method: "POST" },
          token,
          company.id,
        ),
      );
      await onChanged();
    } catch (caught) {
      setMessage(
        caught instanceof Error
          ? caught.message
          : "Saved run could not be reproduced",
      );
    } finally {
      setBusy(false);
    }
  }

  const financialColumn = (column: string) =>
    /(^|_)(debit|credit|amount|balance|variance|budget|actual)(_|$)/i.test(
      column,
    );
  return (
    <div className="report-layout">
      <section className="panel report-controls">
        <div>
          <p className="eyebrow">REPRODUCIBLE OUTPUT</p>
          <h2>Select a report</h2>
        </div>
        <form onSubmit={run}>
          <Field label="Report" htmlFor="standard-report">
            <Select
              value={reportType}
              onChange={(event) => {
                setReportType(event.target.value);
                setResult(null);
              }}
            >
              {REPORT_TYPES.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </Select>
          </Field>
          {reportType === "trial_balance" || reportType === "general_ledger" ? (
            <Field label="Fiscal period" htmlFor="report-period">
              <Select
                value={selectedPeriod}
                onChange={(event) => {
                  setPeriodId(event.target.value);
                  setResult(null);
                }}
              >
                {periods.map((period) => (
                  <option key={period.id} value={period.id}>
                    {period.label} · {period.start_date}
                  </option>
                ))}
              </Select>
            </Field>
          ) : null}
          <Field label="Output" htmlFor="report-format">
            <Select
              value={format}
              onChange={(event) => {
                setFormat(event.target.value);
                setResult(null);
              }}
            >
              <option value="json">Browser</option>
              <option value="pdf">PDF</option>
              <option value="csv">CSV</option>
              <option value="xlsx">Excel</option>
            </Select>
          </Field>
          <Button
            type="submit"
            variant="primary"
            busy={busy}
            disabled={
              (reportType === "trial_balance" ||
                reportType === "general_ledger") &&
              !selectedPeriod
            }
          >
            Run report
          </Button>
        </form>
        {message ? (
          <Banner
            tone={
              /failed|rejected|missing|denied|unavailable|could not/i.test(
                message,
              )
                ? "danger"
                : "success"
            }
          >
            {message}
          </Banner>
        ) : null}
        <h3>Saved runs</h3>
        <div className="saved-runs">
          {runs.slice(0, 12).map((item) => (
            <Button
              key={item.id}
              onClick={() => void reproduce(item.id)}
              disabled={busy}
            >
              <span>{item.report_type.replaceAll("_", " ")}</span>
              <small>{new Date(item.created_at).toLocaleString()}</small>
            </Button>
          ))}
        </div>
      </section>
      <section className="panel report-output">
        {result ? (
          <>
            <div className="section-heading">
              <div>
                <p className="eyebrow">BROWSER REPORT</p>
                <h2>{result.title}</h2>
              </div>
              <Badge tone="success">{result.rows.length} rows</Badge>
            </div>
            <p>
              Digest · <DigestValue value={result.digest} />
            </p>
            <div className="table-wrap">
              <table>
                <caption className="ds-visually-hidden">
                  {result.title} report output
                </caption>
                <thead>
                  <tr>
                    {result.columns.map((column) => (
                      <th key={column}>{column.replaceAll("_", " ")}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {result.rows.map((row, index) => (
                    <tr key={index}>
                      {result.columns.map((column) => (
                        <td key={column}>
                          {financialColumn(column) ? (
                            <AmountCell
                              value={String(row[column] ?? "")}
                              currency={company.base_currency_code}
                              side={
                                column.toLowerCase().includes("debit")
                                  ? "debit"
                                  : column.toLowerCase().includes("credit")
                                    ? "credit"
                                    : undefined
                              }
                            />
                          ) : typeof row[column] === "object" ? (
                            JSON.stringify(row[column])
                          ) : (
                            String(row[column] ?? "")
                          )}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        ) : (
          <EmptyState
            icon="file-text"
            title="Select a report and output format"
            description="Every run saves its parameters and a full content digest for reproduction and audit."
          />
        )}
      </section>
    </div>
  );
}

export default function App() {
  const [session, setSession] = useState<{ token: string; me: Me } | null>(
    null,
  );
  if (!session)
    return <Login onLogin={(token, me) => setSession({ token, me })} />;
  return (
    <Workspace
      token={session.token}
      me={session.me}
      onLogout={() => setSession(null)}
    />
  );
}
