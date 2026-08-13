import React from "react";
import { PageHeader } from "../../components/navigation/PageHeader.jsx";
import { Card } from "../../components/core/Card.jsx";
import { Button } from "../../components/core/Button.jsx";
import { Badge } from "../../components/core/Badge.jsx";
import { Banner } from "../../components/feedback/Banner.jsx";
import { Field } from "../../components/forms/Field.jsx";
import { Select } from "../../components/forms/Select.jsx";
import { DataTable } from "../../components/data/DataTable.jsx";
import { AmountCell } from "../../components/data/AmountCell.jsx";
import { DigestValue } from "../../components/data/DigestValue.jsx";
import { KeyValueList } from "../../components/data/KeyValueList.jsx";
import { EmptyState } from "../../components/feedback/EmptyState.jsx";

const DIGEST = "9f2c41ab77de0031bb51c4e9a2f6d80cc1e5b34a9d77e0f2461a8bb35c07d9e14";

const TB = [
  { code: "1000", name: "Cash and equivalents", debit: 402180.0, credit: 0 },
  { code: "1200", name: "Accounts receivable", debit: 618440.5, credit: 0 },
  { code: "2100", name: "Accrued liabilities", debit: 0, credit: 284900.0 },
  { code: "3200", name: "Retained earnings", debit: 0, credit: 918440.0 },
  { code: "4000", name: "Revenue", debit: 0, credit: 3140800.0 },
  { code: "6000", name: "Cost of sales", debit: 2943840.0, credit: 0 },
  { code: "6400", name: "Professional fees", debit: 380000.0, credit: 0 },
];

const RUNS = [
  { type: "Trial balance", run: "2026-07-31 15:58", period: "P07 FY2026", rows: 7 },
  { type: "General ledger", run: "2026-07-30 09:12", period: "P07 FY2026", rows: 482 },
  { type: "Integrity report", run: "2026-07-29 18:40", period: "—", rows: 2 },
];

export function ReportsScreen({ capabilities = [] }) {
  const [type, setType] = React.useState("trial_balance");
  const [period, setPeriod] = React.useState("7");
  const [state, setState] = React.useState("result");
  const needsPeriod = type === "trial_balance" || type === "general_ledger";

  const invalidate = (setter) => (v) => { setter(v); setState("idle"); };

  return (
    <>
      <PageHeader
        eyebrow="Output"
        title="Reports"
        dataState="current"
        updatedAt="16:04 America/New_York"
        meta="Northstar Manufacturing · NORTHSTAR-01 · base USD"
      />

      <div style={{ display: "grid", gridTemplateColumns: "340px minmax(0,1fr)", gap: "var(--stack-gap)", alignItems: "start" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--stack-gap)" }}>
          <Card title="Run a report">
            <div style={{ display: "flex", flexDirection: "column", gap: "var(--field-gap)" }}>
              <Field label="Report" htmlFor="rt">
                <Select value={type} onChange={(e) => invalidate(setType)(e.target.value)} options={[
                  { value: "trial_balance", label: "Trial balance" },
                  { value: "general_ledger", label: "General ledger listing" },
                  { value: "coa", label: "Chart of accounts" },
                  { value: "groups", label: "Transaction groups" },
                  { value: "prepost", label: "Pre-post journals" },
                  { value: "closing", label: "Closing history" },
                  { value: "integrity", label: "Integrity report" },
                ]} />
              </Field>
              {needsPeriod && (
                <Field label="Fiscal period" htmlFor="rp" required hint="Required for this report.">
                  <Select value={period} onChange={(e) => invalidate(setPeriod)(e.target.value)} options={[
                    { value: "7", label: "P07 · Jul 2026" },
                    { value: "6", label: "P06 · Jun 2026" },
                  ]} />
                </Field>
              )}
              <Field label="Output" htmlFor="ro">
                <Select defaultValue="browser" options={[
                  { value: "browser", label: "Browser" },
                  { value: "pdf", label: "PDF" },
                  { value: "csv", label: "CSV" },
                  { value: "xlsx", label: "Excel" },
                ]} />
              </Field>
              <Button variant="primary" icon="play" fullWidth onClick={() => setState("result")}>Run report</Button>
            </div>
          </Card>

          <Card title="Saved runs" description="Reproduce a prior run's parameters and digest" padded={false}>
            <DataTable
              caption="Saved report runs"
              rows={RUNS}
              rowKey={(r) => r.run}
              columns={[
                { key: "type", header: "Report", wrap: true },
                { key: "run", header: "Run at", mono: true },
                { key: "rows", header: "Rows", align: "right" },
                { key: "act", header: "", render: () => <Button size="sm" variant="ghost" icon="rotate-ccw">Reproduce</Button> },
              ]}
            />
          </Card>
        </div>

        {state === "idle" ? (
          <Card title="No current result">
            <Banner tone="info" title="Parameters changed">
              The previous result was cleared because it no longer matches the parameters you are editing. Run the report to produce a new result.
            </Banner>
          </Card>
        ) : (
          <Card
            title="Trial balance"
            description="Northstar Manufacturing · P07 Jul 2026 · base USD"
            padded={false}
            actions={
              <>
                <Button size="sm" icon="download">PDF</Button>
                <Button size="sm" icon="download">CSV</Button>
                <Button size="sm" icon="download">Excel</Button>
              </>
            }
            footer={<span style={{ display: "inline-flex", alignItems: "center", gap: "var(--space-4)", flexWrap: "wrap" }}>7 rows · run 16:04 America/New_York · content digest <DigestValue value={DIGEST} /></span>}
          >
            <div style={{ padding: "var(--card-pad)", borderBottom: "1px solid var(--border-hairline)" }}>
              <Banner tone="danger" title="Trial balance does not reconcile — debits exceed credits by 320.50 USD">
                This is the same imbalance reported by the latest integrity check. The report is shown as run; the figures are not adjusted to reconcile.
              </Banner>
            </div>
            <DataTable
              caption="Trial balance, period 07 FY2026"
              rows={TB}
              rowKey={(r) => r.code}
              columns={[
                { key: "code", header: "Account", mono: true, width: "96px" },
                { key: "name", header: "Name", wrap: true },
                { key: "debit", header: "Debit", numeric: true, render: (r) => <AmountCell value={r.debit} currency="USD" side="debit" /> },
                { key: "credit", header: "Credit", numeric: true, render: (r) => <AmountCell value={r.credit} currency="USD" side="credit" /> },
              ]}
              footRow={{ name: "Total", debit: <AmountCell value={4344460.5} emphasis />, credit: <AmountCell value={4344140.0} emphasis /> }}
            />
          </Card>
        )}
      </div>
    </>
  );
}
