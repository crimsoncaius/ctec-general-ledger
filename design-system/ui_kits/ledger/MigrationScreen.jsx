import React from "react";
import { PageHeader } from "../../components/navigation/PageHeader.jsx";
import { Card } from "../../components/core/Card.jsx";
import { Button } from "../../components/core/Button.jsx";
import { Badge } from "../../components/core/Badge.jsx";
import { Banner } from "../../components/feedback/Banner.jsx";
import { Dialog } from "../../components/feedback/Dialog.jsx";
import { DataTable } from "../../components/data/DataTable.jsx";
import { AmountCell } from "../../components/data/AmountCell.jsx";
import { StatusPill } from "../../components/data/StatusPill.jsx";
import { DigestValue } from "../../components/data/DigestValue.jsx";
import { KeyValueList } from "../../components/data/KeyValueList.jsx";
import { ProgressBar } from "../../components/feedback/ProgressBar.jsx";

const SOURCE_DIGEST = "4c81e7d2aa39b06f5518c3ea77b41d90ff28c6b5109ae7d3348b2fc61e05a7db";

const EXCEPTIONS = [
  { table: "GLLEDGER", record: 18422, severity: "Blocking", code: "ACCT_MISSING", message: "Account 8150 is not present in GLACCT", blocking: true },
  { table: "GLLEDGER", record: 18519, severity: "Blocking", code: "PERIOD_UNBALANCED", message: "Period 06 debits exceed credits by 320.50", blocking: true },
  { table: "GLACCT", record: 204, severity: "Warning", code: "NAME_TRUNCATED", message: "Account name exceeded 60 characters and was truncated", blocking: false },
];

const RUNS = [
  { source: "northstar_2025.zip", kind: "trial", id: "TRIAL-000031", status: "exception", at: "2026-07-31 15:22" },
  { source: "northstar_2025.zip", kind: "trial", id: "TRIAL-000030", status: "failed", at: "2026-07-31 14:05" },
];

export function MigrationScreen({ capabilities = [] }) {
  const [stage, setStage] = React.useState("exception");
  const [dialog, setDialog] = React.useState(false);
  const applyReady = stage === "ready";

  return (
    <>
      <PageHeader
        eyebrow="Company"
        title="Legacy migration"
        dataState="current"
        updatedAt="16:04 America/New_York"
        meta={<>Target Northstar Manufacturing · <Badge tone="warning">target not empty</Badge></>}
        actions={<Button icon="refresh-cw">Refresh</Button>}
      />

      <Banner tone="info" title="A trial is always read-only" style={{ marginBottom: "var(--stack-gap)" }}>
        Staging reads the DBF snapshots and reconciles them without touching the target company. Nothing is imported until you apply an apply-ready trial.
      </Banner>

      <div style={{ display: "grid", gridTemplateColumns: "340px minmax(0,1fr)", gap: "var(--stack-gap)", alignItems: "start" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--stack-gap)" }}>
          <Card title="1 · Snapshot" description="Flat ZIP of read-only DBF tables">
            <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-5)" }}>
              <div style={{ border: "1px dashed var(--border-strong)", borderRadius: "var(--radius-sm)", padding: "var(--space-7)", textAlign: "center", background: "var(--surface-sunken)" }}>
                <p style={{ font: "var(--type-label)" }}>northstar_2025.zip</p>
                <p style={{ font: "var(--type-caption)", color: "var(--text-muted)", marginTop: "var(--space-2)" }}>GLACCT, GLLEDGER required · GLCURR, GLPREPOST, GLREP optional</p>
              </div>
              <KeyValueList items={[{ label: "Source digest", value: <DigestValue value={SOURCE_DIGEST} label="Source digest" truncate /> }]} />
              <Button variant="secondary" icon="flask-conical" fullWidth onClick={() => setStage("running")}>Stage read-only trial</Button>
            </div>
          </Card>

          <Card title="Run history" padded={false}>
            <DataTable
              caption="Migration trial and apply runs"
              rows={RUNS}
              rowKey={(r) => r.id}
              columns={[
                { key: "id", header: "Run", mono: true },
                { key: "kind", header: "Kind", render: (r) => <StatusPill status={r.kind} size="sm" /> },
                { key: "status", header: "Outcome", render: (r) => <StatusPill status={r.status} size="sm" /> },
                { key: "at", header: "At", mono: true },
              ]}
            />
          </Card>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "var(--stack-gap)" }}>
          {stage === "running" && (
            <Card title="2 · Trial in progress">
              <ProgressBar label="Staging northstar_2025.zip" status="running" value={42} />
              <p style={{ font: "var(--type-caption)", color: "var(--text-muted)", marginTop: "var(--space-4)" }}>
                Durable job. Leaving this page does not cancel it.
              </p>
              <div style={{ marginTop: "var(--space-5)", display: "flex", gap: "var(--space-4)" }}>
                <Button size="sm" onClick={() => setStage("exception")}>Show exception outcome</Button>
                <Button size="sm" onClick={() => setStage("ready")}>Show apply-ready outcome</Button>
              </div>
            </Card>
          )}

          {stage !== "running" && (
            <Card
              title="2 · Trial reconciliation"
              description="TRIAL-000031 · staged 16:22 America/New_York"
              actions={<StatusPill status={applyReady ? "reconciled" : "exception"} />}
              padded={false}
              footer={<span style={{ display: "inline-flex", gap: "var(--space-4)", flexWrap: "wrap", alignItems: "center" }}>Source digest <DigestValue value={SOURCE_DIGEST} label="Source digest" /></span>}
            >
              <div style={{ padding: "var(--card-pad)", display: "flex", flexDirection: "column", gap: "var(--space-6)" }}>
                <KeyValueList
                  columns={4}
                  items={[
                    { label: "Staged rows", value: "48,221", numeric: true },
                    { label: "Blocking rows", value: applyReady ? "0" : "2", numeric: true },
                    { label: "Warnings", value: "1", numeric: true },
                    { label: "Ledger", value: applyReady ? "Balanced" : "Unbalanced" },
                    { label: "Debit total", value: <AmountCell value={4218400.0} currency="USD" />, numeric: true },
                    { label: "Credit total", value: <AmountCell value={applyReady ? 4218400.0 : 4218079.5} currency="USD" />, numeric: true },
                    { label: "Difference", value: <AmountCell value={applyReady ? 0 : 320.5} currency="USD" emphasis />, numeric: true },
                    { label: "Account-period reconciliation", value: applyReady ? "All periods agree" : "2 periods disagree" },
                  ]}
                />
                {!applyReady && (
                  <Banner tone="danger" title="Trial is not apply-ready">
                    Blocking reason: ledger totals differ by 320.50 USD and account 8150 is referenced but missing from GLACCT. Clear both before applying.
                  </Banner>
                )}
              </div>
            </Card>
          )}

          <Card
            title="Record-level exceptions"
            description={applyReady ? "1 warning, no blocking rows" : "2 blocking, 1 warning"}
            padded={false}
            actions={<Button size="sm" icon="download">Exception CSV</Button>}
          >
            <DataTable
              caption="Migration record exceptions"
              rows={applyReady ? EXCEPTIONS.filter((e) => !e.blocking) : EXCEPTIONS}
              rowKey={(r) => r.table + r.record}
              columns={[
                { key: "table", header: "Source table", mono: true },
                { key: "record", header: "Record", mono: true, align: "right" },
                { key: "severity", header: "Severity", render: (r) => <StatusPill status={r.blocking ? "failed" : "partial"} label={r.severity} size="sm" /> },
                { key: "code", header: "Issue", mono: true },
                { key: "message", header: "Message", wrap: true },
              ]}
            />
          </Card>

          <Card title="3 · Apply">
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "var(--space-6)", flexWrap: "wrap" }}>
              <p style={{ font: "var(--type-body-sm)", color: "var(--text-secondary)", maxWidth: "58ch" }}>
                {applyReady
                  ? "The trial is apply-ready. Applying imports accounts, journals, budgets, reports and lineage in one transaction, and requires the exact source digest plus an APPLY confirmation."
                  : "Apply is unavailable: the current trial has blocking rows, and the target company already contains ledger data."}
              </p>
              <Button variant="danger" icon="database-zap" disabled={!applyReady || !capabilities.includes("migration.run")} onClick={() => setDialog(true)}>
                Apply migration
              </Button>
            </div>
          </Card>
        </div>
      </div>

      <Dialog
        open={dialog}
        tone="danger"
        title="Apply legacy migration"
        subject={`TRIAL-000031 · northstar_2025.zip · digest ${SOURCE_DIGEST.slice(0, 12)}…${SOURCE_DIGEST.slice(-8)}`}
        consequence="Accounts, journals, budgets, reports and lineage are imported into Northstar Manufacturing in one transaction. If any record fails, nothing is written and existing target data is left visibly unchanged."
        confirmWord="APPLY"
        confirmLabel="Apply migration"
        onConfirm={() => setDialog(false)}
        onCancel={() => setDialog(false)}
      />
    </>
  );
}
