import { useCallback, useEffect, useState } from "react";
import { api, apiGetDownload, apiUpload } from "./api";
import {
  AmountCell,
  Badge,
  Banner,
  Button,
  Dialog,
  DigestValue,
  Field,
  Input,
  KeyValueList,
  ProgressBar,
  StatusPill,
} from "./design-system";
import type { CompanyAccess, MigrationRun } from "./types";

type Props = { token: string; company: CompanyAccess };

function save(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

export function LegacyMigrationPanel({ token, company }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [runs, setRuns] = useState<MigrationRun[]>([]);
  const [selected, setSelected] = useState<MigrationRun | null>(null);
  const [confirmApply, setConfirmApply] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  const refresh = useCallback(async () => {
    setRuns(
      await api<MigrationRun[]>("/migration/runs", {}, token, company.id),
    );
  }, [company.id, token]);

  useEffect(() => {
    const handle = window.setTimeout(() => {
      void refresh().catch((caught: unknown) =>
        setMessage(
          caught instanceof Error
            ? caught.message
            : "Migration history could not be loaded",
        ),
      );
    }, 0);
    return () => window.clearTimeout(handle);
  }, [refresh]);

  async function stage() {
    if (!file) return;
    setBusy(true);
    setMessage("");
    try {
      const run = await apiUpload<MigrationRun>(
        "/migration/stage",
        file,
        token,
        company.id,
        "archive",
      );
      setSelected(run);
      setMessage(
        run.reconciliation.apply_ready
          ? "Read-only trial migration reconciled and is ready for controlled apply."
          : "Trial migration completed with blocking exceptions; source data was not applied.",
      );
      await refresh();
    } catch (caught) {
      setMessage(
        caught instanceof Error
          ? caught.message
          : "Legacy snapshot could not be staged",
      );
    } finally {
      setBusy(false);
    }
  }

  async function openRun(id: string) {
    setBusy(true);
    try {
      setSelected(
        await api<MigrationRun>(`/migration/runs/${id}`, {}, token, company.id),
      );
    } catch (caught) {
      setMessage(
        caught instanceof Error
          ? caught.message
          : "Migration run could not be opened",
      );
    } finally {
      setBusy(false);
    }
  }

  async function downloadExceptions() {
    if (!selected) return;
    const result = await apiGetDownload(
      `/migration/runs/${selected.id}/exceptions.csv`,
      token,
      company.id,
    );
    save(result.blob, result.filename);
  }

  async function apply() {
    if (!selected) return;
    setBusy(true);
    setMessage("");
    try {
      const result = await api<MigrationRun>(
        `/migration/runs/${selected.id}/apply`,
        {
          method: "POST",
          body: JSON.stringify({
            source_digest: selected.source_digest,
            confirmation: "APPLY",
          }),
        },
        token,
        company.id,
      );
      setSelected(result);
      setConfirmApply(false);
      setMessage(
        "Legacy snapshot applied atomically; accounts, journals, budgets, and lineage were audited.",
      );
      await refresh();
    } catch (caught) {
      setMessage(
        caught instanceof Error
          ? caught.message
          : "Migration could not be applied",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel migration-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">READ-ONLY DBF CUTOVER</p>
          <h2>Legacy migration</h2>
        </div>
        <Badge>ZIP snapshot</Badge>
      </div>
      <p>
        Upload copies of <code>GLACCNT.DAT</code> and <code>GLMAIN.DAT</code>;
        optional currency, pre-post, and report tables are staged too. The
        archive is hashed and read without writing to the source. Apply is
        available only after every blocking exception and reconciliation
        difference is cleared.
      </p>
      <Field
        label="Legacy DBF snapshot"
        htmlFor="legacy-snapshot"
        hint="Selecting another file invalidates the current trial result."
      >
        <Input
          aria-label="Legacy DBF snapshot"
          type="file"
          accept=".zip,application/zip"
          onChange={(event) => {
            setFile(event.target.files?.[0] ?? null);
            setSelected(null);
            setMessage("");
          }}
        />
      </Field>
      <div className="button-row">
        <Button
          variant="primary"
          busy={busy}
          disabled={!file}
          onClick={() => void stage()}
        >
          Run read-only trial
        </Button>
        {selected &&
        (selected.counts.errors ?? 0) + (selected.counts.warnings ?? 0) > 0 ? (
          <Button
            icon="download"
            disabled={busy}
            onClick={() => void downloadExceptions()}
          >
            Download exceptions
          </Button>
        ) : null}
      </div>
      {busy ? (
        <ProgressBar
          label="Legacy migration trial"
          status="running"
          indeterminate
        />
      ) : null}
      {message ? (
        <Banner
          tone={
            message.includes("blocking") || message.includes("could not")
              ? "warning"
              : "success"
          }
        >
          {message}
        </Banner>
      ) : null}

      {selected ? (
        <div className="migration-result">
          <KeyValueList
            columns={4}
            items={[
              {
                label: "Rows staged",
                value: selected.counts.records ?? 0,
                numeric: true,
              },
              {
                label: "Blocking rows",
                value: selected.counts.errors ?? 0,
                numeric: true,
              },
              {
                label: "Warnings",
                value: selected.counts.warnings ?? 0,
                numeric: true,
              },
              {
                label: "Ledger",
                value: (
                  <StatusPill
                    status={
                      selected.reconciliation.ledger_balanced
                        ? "reconciled"
                        : "exception"
                    }
                    label={
                      selected.reconciliation.ledger_balanced
                        ? "Balanced"
                        : "Difference"
                    }
                  />
                ),
              },
            ]}
          />
          <p>
            <strong>Source digest</strong>{" "}
            <DigestValue value={selected.source_digest} label="Source digest" />
          </p>
          <p>
            Debits{" "}
            <AmountCell
              value={selected.reconciliation.ledger_debits ?? "0"}
              side="debit"
              currency={company.base_currency_code}
            />{" "}
            credits{" "}
            <AmountCell
              value={selected.reconciliation.ledger_credits ?? "0"}
              side="credit"
              currency={company.base_currency_code}
            />
            account periods{" "}
            {selected.reconciliation.account_periods_match
              ? "reconcile"
              : "do not reconcile"}
            .
          </p>
          {selected.reconciliation.blocking_reason ? (
            <Banner tone="danger" title="Apply is blocked">
              {selected.reconciliation.blocking_reason}
            </Banner>
          ) : null}
          {selected.staging_records.slice(0, 20).map((row) => (
            <article
              className={`migration-exception ${row.severity}`}
              key={row.id}
            >
              <strong>
                {row.source_table} record {row.source_record}
              </strong>
              {row.issues.map((issue) => (
                <span key={`${row.id}:${issue.code}`}>
                  {issue.code}: {issue.message}
                </span>
              ))}
            </article>
          ))}
          {selected.dry_run && selected.reconciliation.apply_ready ? (
            <div className="migration-apply">
              <p>
                Apply requires an empty target company and commits the entire
                cutover or nothing.
              </p>
              <Button
                variant="danger"
                disabled={busy}
                onClick={() => setConfirmApply(true)}
              >
                Apply reconciled snapshot
              </Button>
              <Dialog
                open={confirmApply}
                tone="danger"
                title="Apply legacy migration"
                subject={`${company.code} · ${selected.source_digest}`}
                consequence="Accounts, journals, budgets, reports and source lineage are imported in one atomic transaction. The target company must be empty."
                confirmWord="APPLY"
                confirmLabel="Apply migration"
                busy={busy}
                onCancel={() => setConfirmApply(false)}
                onConfirm={() => void apply()}
              />
            </div>
          ) : null}
        </div>
      ) : null}

      {runs.length ? (
        <div className="migration-history">
          <h3>Trial and apply history</h3>
          {runs.slice(0, 10).map((run) => (
            <Button key={run.id} onClick={() => void openRun(run.id)}>
              <span>{run.source_path}</span>
              <span>
                <StatusPill
                  status={run.dry_run ? "trial" : "applied"}
                  label={run.dry_run ? "trial" : "applied"}
                />{" "}
                <StatusPill
                  status={
                    run.status === "succeeded"
                      ? "succeeded"
                      : run.status === "failed"
                        ? "failed"
                        : "running"
                  }
                  label={run.status}
                />
              </span>
            </Button>
          ))}
        </div>
      ) : null}
    </section>
  );
}
