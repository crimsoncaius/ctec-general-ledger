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
import { KeyValueList } from "../../components/data/KeyValueList.jsx";
import { Field } from "../../components/forms/Field.jsx";
import { Select } from "../../components/forms/Select.jsx";
import { Textarea } from "../../components/forms/Textarea.jsx";

const ENTRIES = [
  { entry: "JE-2026-000482", desc: "Professional fees, Q3 retainer", posted: "2026-07-28", reversing: false, total: 41000.0 },
  { entry: "JE-2026-000481", desc: "Intercompany rebill — Harbour", posted: "2026-07-27", reversing: false, total: 12480.0 },
  { entry: "JE-2026-000475", desc: "Reversal of JE-2026-000468", posted: "2026-07-24", reversing: true, total: 3200.0 },
];

const LINES = [
  { code: "6400", name: "Professional fees", debit: 41000.0, credit: 0 },
  { code: "2100", name: "Accrued liabilities", debit: 0, credit: 41000.0 },
];

export function InquiryScreen({ capabilities = [] }) {
  const [selected, setSelected] = React.useState("JE-2026-000482");
  const [reversing, setReversing] = React.useState(false);
  const [reason, setReason] = React.useState("");
  const [posted, setPosted] = React.useState(null);
  const entry = ENTRIES.find((e) => e.entry === selected);
  const canReverse = capabilities.includes("journals.reverse") && entry && !entry.reversing;

  return (
    <>
      <PageHeader
        eyebrow="Ledger"
        title="Posted inquiry"
        dataState="current"
        updatedAt="16:04 America/New_York"
        meta="FY2026 · 148 posted entries · base USD"
        actions={<Button icon="refresh-cw">Refresh</Button>}
      />

      {posted && (
        <Banner tone="success" title={`Reversal ${posted} posted`} style={{ marginBottom: "var(--stack-gap)" }}>
          A new equal-and-opposite entry was posted into P07 and linked to {selected}. The original entry remains visible and unchanged.
        </Banner>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "minmax(0,1fr) minmax(0,1.4fr)", gap: "var(--stack-gap)", alignItems: "start" }}>
        <Card title="Posted entries" padded={false} footer="Posted entries cannot be edited or deleted.">
          <DataTable
            caption="Posted journal entries"
            rows={ENTRIES.map((e) => ({ ...e, selected: e.entry === selected }))}
            rowKey={(r) => r.entry}
            onRowClick={(r) => { setSelected(r.entry); setPosted(null); }}
            columns={[
              { key: "entry", header: "Entry", mono: true },
              { key: "desc", header: "Description", wrap: true },
              { key: "posted", header: "Posted", mono: true },
              { key: "total", header: "Total", numeric: true, render: (r) => <AmountCell value={r.total} currency="USD" /> },
            ]}
          />
        </Card>

        <div style={{ display: "flex", flexDirection: "column", gap: "var(--stack-gap)" }}>
          <Card
            title={entry.entry}
            description={entry.desc}
            actions={
              <>
                <StatusPill status="posted" />
                {entry.reversing && <StatusPill status="reversed" label="Reversing entry" />}
              </>
            }
            padded={false}
            footer={entry.reversing ? <>Linked original <Badge mono>JE-2026-000468</Badge></> : "Corrections post a new linked reversal; the original is never rewritten."}
          >
            <div style={{ padding: "var(--card-pad)", borderBottom: "1px solid var(--border-hairline)" }}>
              <KeyValueList
                columns={3}
                items={[
                  { label: "Posting date", value: entry.posted, mono: true },
                  { label: "Period", value: "P07 · Jul 2026", mono: true },
                  { label: "Reversing entry", value: entry.reversing ? "Yes" : "No" },
                ]}
              />
            </div>
            <DataTable
              caption={`Lines of ${entry.entry}`}
              rows={LINES}
              rowKey={(r) => r.code}
              columns={[
                { key: "code", header: "Account", mono: true, width: "96px" },
                { key: "name", header: "Name", wrap: true },
                { key: "debit", header: "Debit", numeric: true, render: (r) => <AmountCell value={r.debit} currency="USD" side="debit" /> },
                { key: "credit", header: "Credit", numeric: true, render: (r) => <AmountCell value={r.credit} currency="USD" side="credit" /> },
              ]}
              footRow={{ name: "Total", debit: <AmountCell value={41000} emphasis />, credit: <AmountCell value={41000} emphasis /> }}
            />
          </Card>

          {canReverse ? (
            <Card title="Correct with a reversal" description="Posts a new equal-and-opposite entry. The original is not edited.">
              <div style={{ display: "flex", flexDirection: "column", gap: "var(--field-gap)" }}>
                <div style={{ display: "grid", gridTemplateColumns: "220px minmax(0,1fr)", gap: "var(--space-6)" }}>
                  <Field label="Reversal period" htmlFor="rp" hint="An open period is required.">
                    <Select options={[{ value: "7", label: "P07 · Jul 2026" }]} />
                  </Field>
                  <Field label="Reason" htmlFor="rr" required hint="Recorded in the audit trail with your identity.">
                    <Textarea rows={2} value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Why is this entry being reversed?" />
                  </Field>
                </div>
                <div style={{ display: "flex", justifyContent: "flex-end" }}>
                  <Button variant="primary" icon="undo-2" disabled={reason.trim().length < 4} onClick={() => setReversing(true)}>Post reversal</Button>
                </div>
                {reason.trim().length < 4 && (
                  <p style={{ font: "var(--type-caption)", color: "var(--text-muted)", textAlign: "right" }}>A reason is required before a reversal can be posted.</p>
                )}
              </div>
            </Card>
          ) : (
            <Card title="Reversal">
              <p style={{ font: "var(--type-body-sm)", color: "var(--text-secondary)" }}>
                {entry.reversing
                  ? "This entry is itself a reversal, so it cannot be reversed again."
                  : "Reversal requires the journals.reverse capability, which is not part of your access."}
              </p>
            </Card>
          )}
        </div>
      </div>

      <Dialog
        open={reversing}
        title="Post reversal entry"
        subject={`Original ${entry.entry} · 41,000.00 USD`}
        consequence="This posts a new equal-and-opposite entry into P07 Jul 2026 and links it to the original. The original entry is not edited or deleted."
        confirmLabel="Post reversal"
        onConfirm={() => { setReversing(false); setPosted("JE-2026-000483"); }}
        onCancel={() => setReversing(false)}
      />
    </>
  );
}
