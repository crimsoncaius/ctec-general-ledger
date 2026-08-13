import React from "react";
import { PageHeader } from "../../components/navigation/PageHeader.jsx";
import { Tabs } from "../../components/navigation/Tabs.jsx";
import { Card } from "../../components/core/Card.jsx";
import { Button } from "../../components/core/Button.jsx";
import { Badge } from "../../components/core/Badge.jsx";
import { Banner } from "../../components/feedback/Banner.jsx";
import { Dialog } from "../../components/feedback/Dialog.jsx";
import { DataTable } from "../../components/data/DataTable.jsx";
import { StatusPill } from "../../components/data/StatusPill.jsx";
import { AmountCell } from "../../components/data/AmountCell.jsx";
import { KeyValueList } from "../../components/data/KeyValueList.jsx";
import { Checkbox } from "../../components/forms/Checkbox.jsx";
import { EmptyState } from "../../components/feedback/EmptyState.jsx";

const ROWS = [
  { batch: "BATCH-000151", desc: "July payroll accrual", status: "draft", entries: 4, total: 84320.0, preparer: "L. Osei", next: "Validate" },
  { batch: "BATCH-000152", desc: "Depreciation, plant assets", status: "draft", entries: 3, total: 18400.0, preparer: "L. Osei", next: "Validate" },
  { batch: "BATCH-000153", desc: "Bank fees, July", status: "draft", entries: 1, total: 240.0, preparer: "L. Osei", next: "Validate" },
  { batch: "BATCH-000150", desc: "Intercompany rebill — Harbour", status: "validated", entries: 2, total: 12480.0, preparer: "L. Osei", next: "Approve" },
  { batch: "BATCH-000149", desc: "FX revaluation, EUR positions", status: "approved", entries: 6, total: 5218.44, preparer: "L. Osei", next: "Post" },
  { batch: "BATCH-000148", desc: "Professional fees, Q3 retainer", status: "posted", entries: 12, total: 41000.0, preparer: "L. Osei", next: "—" },
];

const NEXT_CAP = { Validate: "journals.validate", Approve: "journals.approve", Post: "journals.post" };

export function JournalsScreen({ capabilities = [], user = "A. Mensah", onGo }) {
  const [tab, setTab] = React.useState("all");
  const [records, setRecords] = React.useState(ROWS);
  const [marked, setMarked] = React.useState(["BATCH-000151", "BATCH-000152"]);
  const [dialog, setDialog] = React.useState(null);
  const [result, setResult] = React.useState(null);
  const [selected, setSelected] = React.useState("BATCH-000150");

  const rows = tab === "all" ? records : records.filter((r) => r.status === tab);
  const detail = records.find((r) => r.batch === selected);
  const toggle = (b) => setMarked((m) => (m.includes(b) ? m.filter((x) => x !== b) : [...m, b]));
  const can = (next) => capabilities.includes(NEXT_CAP[next] || "");
  const countStatus = (status) => records.filter((r) => r.status === status).length;

  const runBulk = () => {
    const attempted = [...marked];
    const failed = attempted.filter((batch) => batch === "BATCH-000152");
    const succeeded = attempted.filter((batch) => !failed.includes(batch));

    setRecords((current) => current.map((row) => (
      succeeded.includes(row.batch) ? { ...row, status: "validated", next: "Approve" } : row
    )));
    setMarked(failed);
    setSelected(failed[0] || succeeded[0] || selected);
    setDialog(null);
    setResult({
      tone: failed.length ? "warning" : "success",
      title: failed.length
        ? `Partial success — ${succeeded.length} of ${attempted.length} batches validated`
        : `${succeeded.length} ${succeeded.length === 1 ? "batch" : "batches"} validated`,
      body: [
        succeeded.length ? `${succeeded.join(", ")} advanced to validated.` : "",
        failed.length ? `${failed.join(", ")} failed: account 6800 is inactive.` : "",
      ].filter(Boolean).join(" "),
      failedBatch: failed[0],
    });
  };

  return (
    <>
      <PageHeader
        eyebrow="Ledger"
        title="Journal batches"
        dataState="current"
        updatedAt="16:04 America/New_York"
        meta={<>FY2026 · P07 open · base USD · <Badge mono>42 batches</Badge></>}
        actions={
          <>
            <Button icon="refresh-cw">Refresh</Button>
            {capabilities.includes("journals.create") && <Button variant="primary" icon="plus">New draft</Button>}
          </>
        }
      />

      {result && (
        <Banner tone={result.tone} title={result.title} onDismiss={() => setResult(null)} style={{ marginBottom: "var(--stack-gap)" }}
          actions={result.failedBatch ? <Button size="sm" variant="secondary" onClick={() => setSelected(result.failedBatch)}>View failed batch</Button> : null}>
          {result.body}
        </Banner>
      )}

      {!capabilities.includes("journals.approve") && capabilities.includes("journals.create") && (
        <Banner tone="info" title="Maker-checker separation applies" style={{ marginBottom: "var(--stack-gap)" }}>
          You can prepare and validate batches. Approval and posting are performed by a different user, so those controls are not shown here.
        </Banner>
      )}

      <Tabs
        activeId={tab}
        onChange={setTab}
        tabs={[
          { id: "all", label: "All", count: records.length },
          { id: "draft", label: "Drafts", count: countStatus("draft") },
          { id: "validated", label: "Validated", count: countStatus("validated") },
          { id: "approved", label: "Approved", count: countStatus("approved") },
          { id: "posted", label: "Posted", count: countStatus("posted") },
        ]}
        style={{ marginBottom: "var(--stack-gap)" }}
      />

      <div style={{ display: "grid", gridTemplateColumns: "minmax(0,2fr) minmax(0,1fr)", gap: "var(--stack-gap)", alignItems: "start" }}>
        <Card
          padded={false}
          title="Batches"
          description={marked.length ? `${marked.length} marked` : "Mark drafts to apply a bulk transition"}
          actions={
            marked.length && capabilities.includes("journals.validate") ? (
              <Button size="sm" variant="primary" icon="list-checks" onClick={() => setDialog("bulk")}>
                Validate {marked.length} marked
              </Button>
            ) : null
          }
          footer={<>Bulk transitions report succeeded and failed items individually.</>}
        >
          {rows.length === 0 ? (
            <EmptyState kind="no-match" icon="search-x" title="No batches in this status" description="Switch tabs to see batches in other states." />
          ) : (
            <DataTable
              caption="Journal batches in the active company"
              rows={rows.map((r) => ({ ...r, selected: r.batch === selected }))}
              rowKey={(r) => r.batch}
              onRowClick={(r) => setSelected(r.batch)}
              columns={[
                {
                  key: "mark",
                  header: <span style={{ position: "absolute", width: 1, height: 1, overflow: "hidden" }}>Marked</span>,
                  width: "34px",
                  render: (r) =>
                    r.status === "draft" ? (
                      <Checkbox checked={marked.includes(r.batch)} onChange={() => toggle(r.batch)} aria-label={`Mark ${r.batch}`} />
                    ) : null,
                },
                { key: "batch", header: "Batch", mono: true },
                { key: "desc", header: "Description", wrap: true },
                { key: "status", header: "Status", render: (r) => <StatusPill status={r.status} size="sm" /> },
                { key: "entries", header: "Entries", align: "right" },
                { key: "total", header: "Total", numeric: true, render: (r) => <AmountCell value={r.total} currency="USD" /> },
                {
                  key: "next",
                  header: "Next action",
                  render: (r) =>
                    r.next === "—" ? (
                      <span style={{ color: "var(--text-muted)" }}>—</span>
                    ) : can(r.next) ? (
                      <Button size="sm" variant={r.next === "Post" ? "primary" : "secondary"} onClick={() => setDialog(r.next)}>{r.next}</Button>
                    ) : (
                      <span style={{ font: "var(--type-caption)", color: "var(--text-muted)" }}>{r.next} — not permitted</span>
                    ),
                },
              ]}
            />
          )}
        </Card>

        <Card
          title={detail ? detail.batch : "No batch selected"}
          description={detail ? detail.desc : undefined}
          footer={detail && detail.status === "posted" ? "Posted content is immutable. Correct it with a linked reversal." : "Draft controls disappear once a batch leaves draft state."}
        >
          {detail && (
            <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-6)" }}>
              <StatusPill status={detail.status} />
              <KeyValueList
                columns={2}
                items={[
                  { label: "Prepared by", value: detail.preparer },
                  { label: "Entries", value: String(detail.entries), numeric: true },
                  { label: "Period", value: "P07 · Jul 2026", mono: true },
                  { label: "Base total", value: <AmountCell value={detail.total} currency="USD" />, numeric: true },
                ]}
              />
              {detail.status === "validated" && (
                <Banner tone="info" title="Prepared by another user">
                  {detail.preparer} prepared this batch, so you may approve it. Self-approval requires an explicit grant.
                </Banner>
              )}
              <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-4)" }}>
                {detail.status === "draft" && capabilities.includes("journals.update") && (
                  <>
                    <Button size="sm" icon="pencil-line">Edit</Button>
                    <Button size="sm" icon="copy">Copy</Button>
                    <Button size="sm" variant="danger" icon="trash-2" onClick={() => setDialog("Delete")}>Delete</Button>
                  </>
                )}
                {detail.status === "posted" && capabilities.includes("journals.reverse") && (
                  <Button size="sm" icon="undo-2" onClick={() => onGo && onGo("inquiry")}>Open in inquiry to reverse</Button>
                )}
              </div>
            </div>
          )}
        </Card>
      </div>

      <Dialog
        open={dialog === "bulk"}
        title={`Validate ${marked.length} marked ${marked.length === 1 ? "batch" : "batches"}`}
        subject={marked.join(", ")}
        consequence="Validation rechecks the open period, account state, currency rules, line sides and base-currency balance for each batch. Batches that fail are left unchanged and reported individually."
        confirmLabel="Validate marked"
        onConfirm={runBulk}
        onCancel={() => setDialog(null)}
      />
      <Dialog
        open={dialog === "Post"}
        tone="neutral"
        title="Post batch"
        subject="BATCH-000149 · 6 entries · 5,218.44 USD"
        consequence="Posting revalidates the batch, then commits entry state, balances, evidence and audit history in one transaction. Posted detail can never be edited — corrections are new linked reversal entries."
        confirmLabel="Post batch"
        onConfirm={() => { setDialog(null); setResult({ tone: "success", title: "BATCH-000149 posted", body: "Six entries committed atomically at 16:07 America/New_York. Detail is now immutable in Posted inquiry." }); }}
        onCancel={() => setDialog(null)}
      />
      <Dialog
        open={dialog === "Approve"}
        title="Approve batch"
        subject="BATCH-000150 · prepared by L. Osei"
        consequence="Approval records you as checker. It does not post the batch and does not alter the preparer's detail."
        confirmLabel="Approve"
        onConfirm={() => { setDialog(null); setResult({ tone: "success", title: "BATCH-000150 approved", body: "Approved by " + user + ". The batch is now eligible for posting." }); }}
        onCancel={() => setDialog(null)}
      />
      <Dialog
        open={dialog === "Validate"}
        title="Validate batch"
        subject="BATCH-000151 · 4 entries"
        consequence="Validation checks the batch against the open period, account state and base-currency balance. Nothing is posted."
        confirmLabel="Validate"
        onConfirm={() => { setDialog(null); setResult({ tone: "success", title: "BATCH-000151 validated", body: "Four entries balanced in USD against period 07." }); }}
        onCancel={() => setDialog(null)}
      />
      <Dialog
        open={dialog === "Delete"}
        tone="danger"
        title="Delete draft batch"
        subject={detail ? `${detail.batch} · ${detail.desc}` : ""}
        consequence="This draft and its unposted entries are removed. No posted history is affected. Other batches are untouched."
        confirmLabel="Delete draft"
        onConfirm={() => { setDialog(null); setResult({ tone: "success", title: "Draft deleted", body: "BATCH-000151 is no longer present. 41 batches remain in this company." }); }}
        onCancel={() => setDialog(null)}
      />
    </>
  );
}
