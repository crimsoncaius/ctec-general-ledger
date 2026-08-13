import React from "react";
import { PageHeader } from "../../components/navigation/PageHeader.jsx";
import { Card } from "../../components/core/Card.jsx";
import { Button } from "../../components/core/Button.jsx";
import { Banner } from "../../components/feedback/Banner.jsx";
import { Dialog } from "../../components/feedback/Dialog.jsx";
import { Field } from "../../components/forms/Field.jsx";
import { Select } from "../../components/forms/Select.jsx";
import { DataTable } from "../../components/data/DataTable.jsx";
import { AmountCell } from "../../components/data/AmountCell.jsx";
import { StatusPill } from "../../components/data/StatusPill.jsx";
import { KeyValueList } from "../../components/data/KeyValueList.jsx";
import { EmptyState } from "../../components/feedback/EmptyState.jsx";

const LINES = [
  { code: "3200", name: "Retained earnings", debit: 0, credit: 918440.0, kind: "Closing" },
  { code: "4000", name: "Revenue", debit: 3140800.0, credit: 0, kind: "Closing" },
  { code: "6000", name: "Cost of sales", debit: 0, credit: 1842360.0, kind: "Closing" },
  { code: "6400", name: "Professional fees", debit: 0, credit: 380000.0, kind: "Closing" },
  { code: "1000", name: "Cash and equivalents — opening", debit: 402180.0, credit: 0, kind: "Opening" },
];

export function CloseScreen({ capabilities = [] }) {
  const [year, setYear] = React.useState("2026");
  const [period, setPeriod] = React.useState("2027-01");
  const [preview, setPreview] = React.useState("balanced");
  const [dialog, setDialog] = React.useState(false);
  const [done, setDone] = React.useState(false);
  const stale = preview === "stale";

  const invalidate = (setter) => (v) => { setter(v); setPreview("stale"); };

  return (
    <>
      <PageHeader
        eyebrow="Close & planning"
        title="Fiscal close"
        dataState="current"
        updatedAt="16:04 America/New_York"
        meta="Northstar Manufacturing · FY2026 open · base USD"
      />

      {done && (
        <Banner tone="success" title="FY2026 closed" style={{ marginBottom: "var(--stack-gap)" }}>
          Retained-earnings and opening entries were posted immutably into P01 FY2027 at 16:11. The close is recorded; FY2026 can no longer be closed again.
        </Banner>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "360px minmax(0,1fr)", gap: "var(--stack-gap)", alignItems: "start" }}>
        <Card title="1 · Prepare" description="Choose the year to close and the period the opening entries land in">
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--field-gap)" }}>
            <Field label="Fiscal year to close" htmlFor="fy" hint="Only open years are eligible.">
              <Select value={year} onChange={(e) => invalidate(setYear)(e.target.value)} options={[
                { value: "2026", label: "FY2026 · open" },
                { value: "2025", label: "FY2025 · closed", disabled: true },
              ]} />
            </Field>
            <Field label="Opening period" htmlFor="op" hint="Must be later than every period in the closing year.">
              <Select value={period} onChange={(e) => invalidate(setPeriod)(e.target.value)} options={[
                { value: "2027-01", label: "P01 · Jan 2027" },
                { value: "2027-02", label: "P02 · Feb 2027" },
              ]} />
            </Field>
            <Button variant="secondary" icon="scale" onClick={() => setPreview("balanced")} fullWidth>Generate preview</Button>
            <p style={{ font: "var(--type-caption)", color: "var(--text-muted)" }}>
              Closing appends retained-earnings and opening entries. It never deletes or rewrites journals.
            </p>
          </div>
        </Card>

        <div style={{ display: "flex", flexDirection: "column", gap: "var(--stack-gap)" }}>
          {stale ? (
            <Card title="2 · Review">
              <Banner tone="warning" title="Preview no longer matches your selection" actions={<Button size="sm" variant="secondary" onClick={() => setPreview("balanced")}>Generate preview</Button>}>
                You changed the fiscal year or opening period, so the earlier preview was discarded. Execution stays unavailable until a balanced preview exists for the current selection.
              </Banner>
            </Card>
          ) : (
            <Card
              title="2 · Review preview"
              description="FY2026 → P01 Jan 2027"
              actions={<StatusPill status="reconciled" />}
              padded={false}
              footer="Preview only. Nothing has been posted."
            >
              <div style={{ padding: "var(--card-pad)", borderBottom: "1px solid var(--border-hairline)" }}>
                <KeyValueList
                  columns={4}
                  items={[
                    { label: "Profit / loss", value: <AmountCell value={918440.0} currency="USD" emphasis />, numeric: true },
                    { label: "Closing lines", value: "4", numeric: true },
                    { label: "Opening lines", value: "1", numeric: true },
                    { label: "Difference", value: <AmountCell value={0} currency="USD" />, numeric: true },
                  ]}
                />
              </div>
              <DataTable
                caption="Closing and opening lines that will be posted"
                rows={LINES}
                rowKey={(r) => r.code + r.kind}
                columns={[
                  { key: "kind", header: "Set" },
                  { key: "code", header: "Account", mono: true },
                  { key: "name", header: "Name", wrap: true },
                  { key: "debit", header: "Debit", numeric: true, render: (r) => <AmountCell value={r.debit} currency="USD" side="debit" /> },
                  { key: "credit", header: "Credit", numeric: true, render: (r) => <AmountCell value={r.credit} currency="USD" side="credit" /> },
                ]}
                footRow={{ name: "Total", debit: <AmountCell value={3542980.0} emphasis />, credit: <AmountCell value={3542980.0} emphasis /> }}
              />
            </Card>
          )}

          <Card title="3 · Execute">
            {capabilities.includes("fiscal.close") ? (
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "var(--space-6)", flexWrap: "wrap" }}>
                <p style={{ font: "var(--type-body-sm)", color: "var(--text-secondary)", maxWidth: "56ch" }}>
                  {done
                    ? "FY2026 is closed. A repeat close is not possible."
                    : stale
                    ? "Execution is unavailable: the current selection has no balanced preview."
                    : "The preview reconciles. Executing posts the closing and opening entries in one transaction and records the close."}
                </p>
                <Button variant="danger" icon="lock" disabled={stale || done} onClick={() => setDialog(true)}>Execute close</Button>
              </div>
            ) : (
              <EmptyState kind="no-action" icon="lock" title="Closing is not part of your access" description="Fiscal close requires the fiscal.close capability. Ask an administrator if you need it." />
            )}
          </Card>
        </div>
      </div>

      <Dialog
        open={dialog}
        tone="danger"
        title="Execute fiscal close"
        subject="FY2026 → opening period P01 Jan 2027 · Northstar Manufacturing"
        consequence="Closing appends immutable retained-earnings and opening entries totalling 3,542,980.00 USD and records the close. Existing journals are never deleted or rewritten. FY2026 cannot be closed again."
        confirmLabel="Execute close"
        onConfirm={() => { setDialog(false); setDone(true); }}
        onCancel={() => setDialog(false)}
      />
    </>
  );
}
