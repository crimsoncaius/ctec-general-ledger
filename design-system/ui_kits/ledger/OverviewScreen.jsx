import React from "react";
import { PageHeader } from "../../components/navigation/PageHeader.jsx";
import { Card } from "../../components/core/Card.jsx";
import { Button } from "../../components/core/Button.jsx";
import { Banner } from "../../components/feedback/Banner.jsx";
import { DataTable } from "../../components/data/DataTable.jsx";
import { StatusPill } from "../../components/data/StatusPill.jsx";
import { AmountCell } from "../../components/data/AmountCell.jsx";
import { KeyValueList } from "../../components/data/KeyValueList.jsx";
import { ProgressBar } from "../../components/feedback/ProgressBar.jsx";

const BATCHES = [
  { batch: "BATCH-000151", desc: "July payroll accrual", status: "draft", entries: 4, total: 84320.0, created: "2026-07-30" },
  { batch: "BATCH-000150", desc: "Intercompany rebill — Harbour", status: "validated", entries: 2, total: 12480.0, created: "2026-07-29" },
  { batch: "BATCH-000149", desc: "FX revaluation, EUR positions", status: "approved", entries: 6, total: 5218.44, created: "2026-07-29" },
  { batch: "BATCH-000148", desc: "Professional fees, Q3 retainer", status: "posted", entries: 12, total: 41000.0, created: "2026-07-28" },
];

export function OverviewScreen({ capabilities = [], onGo, integrity = "exception", jobRunning = false }) {
  return (
    <>
      <PageHeader
        eyebrow="Company"
        title="Overview"
        dataState="current"
        updatedAt="16:04 America/New_York"
        meta="Northstar Manufacturing · NORTHSTAR-01 · FY2026 · base USD"
        actions={
          <>
            <Button icon="refresh-cw">Refresh</Button>
            {capabilities.includes("integrity.run") && <Button variant="primary" icon="scale">Run integrity check</Button>}
          </>
        }
      />

      {integrity === "exception" && (
        <Banner
          tone="danger"
          title="Integrity exception — ledger out of balance by 320.50 USD"
          actions={<><Button size="sm" variant="secondary" onClick={() => onGo && onGo("reports")}>Open integrity report</Button><Button size="sm" variant="ghost">Re-run check</Button></>}
          style={{ marginBottom: "var(--stack-gap)" }}
        >
          Detected in period 07 across two accounts. Posted history is unchanged; investigate before closing the year.
        </Banner>
      )}

      {jobRunning && (
        <Card style={{ marginBottom: "var(--stack-gap)" }}>
          <ProgressBar label="Integrity check · started 16:05" status="running" value={64} />
          <p style={{ font: "var(--type-caption)", color: "var(--text-muted)", marginTop: "var(--space-4)" }}>
            This job runs on the server. You can navigate away without cancelling it.
          </p>
        </Card>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "minmax(0,2.2fr) minmax(0,1fr)", gap: "var(--stack-gap)", alignItems: "start" }}>
        <Card
          title="Recent journal batches"
          description="Newest first, across all statuses"
          padded={false}
          actions={<Button size="sm" iconAfter="arrow-right" onClick={() => onGo && onGo("journals")}>Enter journal work</Button>}
          footer="Showing 4 of 42 batches in this company"
        >
          <DataTable
            caption="Recent journal batches"
            columns={[
              { key: "batch", header: "Batch", mono: true },
              { key: "desc", header: "Description", wrap: true },
              { key: "status", header: "Status", render: (r) => <StatusPill status={r.status} size="sm" /> },
              { key: "entries", header: "Entries", align: "right" },
              { key: "total", header: "Total", numeric: true, render: (r) => <AmountCell value={r.total} currency="USD" /> },
              { key: "created", header: "Created", mono: true },
            ]}
            rows={BATCHES}
            rowKey={(r) => r.batch}
          />
        </Card>

        <div style={{ display: "flex", flexDirection: "column", gap: "var(--stack-gap)" }}>
          <Card title="Books at a glance">
            <KeyValueList
              items={[
                { label: "Posted batches", value: "148", numeric: true },
                { label: "Awaiting approval", value: "2 validated batches", numeric: true },
                { label: "Open period", value: "P07 · 1–31 Jul 2026", mono: true },
                { label: "Fiscal year", value: "FY2026 · open", mono: true },
              ]}
            />
          </Card>
          <Card title="Latest integrity check" footer="Run by A. Mensah · 2026-07-31 15:58">
            <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-5)" }}>
              <StatusPill status="exception" />
              <KeyValueList
                items={[
                  { label: "Debits", value: <AmountCell value={4218400.0} currency="USD" />, numeric: true },
                  { label: "Credits", value: <AmountCell value={4218079.5} currency="USD" />, numeric: true },
                  { label: "Difference", value: <AmountCell value={320.5} currency="USD" emphasis />, numeric: true },
                ]}
              />
            </div>
          </Card>
        </div>
      </div>
    </>
  );
}
