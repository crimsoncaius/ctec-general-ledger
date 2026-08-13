import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { api, apiDownload } from "./api";
import {
  AmountCell,
  Badge,
  Banner,
  Button,
  Checkbox,
  DigestValue,
  Field,
  Input,
  Select,
  StatusPill,
  Switch,
  Textarea,
} from "./design-system";
import type {
  CompanyAccess,
  CustomReportColumn,
  CustomReportDefinition,
  CustomReportDefinitionData,
  CustomReportRow,
  LegacyConversion,
  Period,
  ReportResult,
} from "./types";

type Props = {
  token: string;
  company: CompanyAccess;
  periods: Period[];
  canDesign: boolean;
};

function initialDefinition(periodId: string): CustomReportDefinitionData {
  return {
    title: "Management statement — {company_name} — {period_label}",
    columns: [
      {
        key: "actual",
        label: "Actual",
        kind: "balance",
        period_id: periodId,
        scope: "ytd",
      },
      {
        key: "budget",
        label: "Budget",
        kind: "budget",
        period_id: periodId,
        scope: "ytd",
        scenario: "Current",
      },
      {
        key: "variance",
        label: "Variance",
        kind: "formula",
        scope: "period",
        formula: "actual - budget",
      },
    ],
    rows: [
      { key: "cash", label: "Cash", kind: "account", account_code: "1000" },
      { key: "sales", label: "Sales", kind: "account", account_code: "4000" },
      {
        key: "net",
        label: "Net movement",
        kind: "formula",
        formula: "cash + sales",
        bold: true,
      },
    ],
    sections: [
      { title: "Operating result", row_keys: ["cash", "sales", "net"] },
    ],
    formatting: { decimals: 2 },
  };
}

function ColumnEditor({
  column,
  periods,
  onChange,
  onRemove,
}: {
  column: CustomReportColumn;
  periods: Period[];
  onChange: (value: CustomReportColumn) => void;
  onRemove: () => void;
}) {
  const prefix = `column-${column.key}`;
  return (
    <article className="designer-card">
      <div className="designer-card-head">
        <strong>{column.key}</strong>
        <Button size="sm" type="button" onClick={onRemove}>
          Remove
        </Button>
      </div>
      <Field label="Key" htmlFor={`${prefix}-key`}>
        <Input
          value={column.key}
          onChange={(event) =>
            onChange({
              ...column,
              key: event.target.value.toLowerCase().replace(/[^a-z0-9_]/g, ""),
            })
          }
        />
      </Field>
      <Field label="Label" htmlFor={`${prefix}-label`}>
        <Input
          value={column.label}
          onChange={(event) =>
            onChange({ ...column, label: event.target.value })
          }
        />
      </Field>
      <Field label="Source" htmlFor={`${prefix}-source`}>
        <Select
          value={column.kind}
          onChange={(event) =>
            onChange({
              ...column,
              kind: event.target.value as CustomReportColumn["kind"],
            })
          }
        >
          <option value="balance">Ledger balance</option>
          <option value="budget">Budget</option>
          <option value="formula">Formula</option>
        </Select>
      </Field>
      {column.kind === "formula" ? (
        <Field label="Formula" htmlFor={`${prefix}-formula`}>
          <Input
            value={column.formula ?? ""}
            onChange={(event) =>
              onChange({ ...column, formula: event.target.value })
            }
            placeholder="actual - budget"
          />
        </Field>
      ) : (
        <>
          <Field label="Period" htmlFor={`${prefix}-period`}>
            <Select
              value={column.period_id || periods[0]?.id || ""}
              onChange={(event) =>
                onChange({ ...column, period_id: event.target.value })
              }
            >
              {periods.map((period) => (
                <option value={period.id} key={period.id}>
                  {period.label}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Scope" htmlFor={`${prefix}-scope`}>
            <Select
              value={column.scope}
              onChange={(event) =>
                onChange({
                  ...column,
                  scope: event.target.value as CustomReportColumn["scope"],
                })
              }
            >
              <option value="period">Selected period</option>
              <option value="ytd">Year to date</option>
            </Select>
          </Field>
          {column.kind === "budget" ? (
            <Field label="Scenario" htmlFor={`${prefix}-scenario`}>
              <Input
                value={column.scenario ?? "Current"}
                onChange={(event) =>
                  onChange({ ...column, scenario: event.target.value })
                }
              />
            </Field>
          ) : null}
        </>
      )}
    </article>
  );
}

function RowEditor({
  row,
  onChange,
  onRemove,
}: {
  row: CustomReportRow;
  onChange: (value: CustomReportRow) => void;
  onRemove: () => void;
}) {
  const prefix = `row-${row.key}`;
  return (
    <article className="designer-card row-card">
      <div className="designer-card-head">
        <strong>{row.key}</strong>
        <Button size="sm" type="button" onClick={onRemove}>
          Remove
        </Button>
      </div>
      <Field label="Key" htmlFor={`${prefix}-key`}>
        <Input
          value={row.key}
          onChange={(event) =>
            onChange({
              ...row,
              key: event.target.value.toLowerCase().replace(/[^a-z0-9_]/g, ""),
            })
          }
        />
      </Field>
      <Field label="Label" htmlFor={`${prefix}-label`}>
        <Input
          value={row.label}
          onChange={(event) => onChange({ ...row, label: event.target.value })}
        />
      </Field>
      <Field label="Row type" htmlFor={`${prefix}-type`}>
        <Select
          value={row.kind}
          onChange={(event) =>
            onChange({
              ...row,
              kind: event.target.value as CustomReportRow["kind"],
            })
          }
        >
          <option value="account">Account</option>
          <option value="range">Account range</option>
          <option value="formula">Formula</option>
          <option value="heading">Heading</option>
          <option value="spacer">Spacer</option>
        </Select>
      </Field>
      {row.kind === "account" ? (
        <Field label="Account code" htmlFor={`${prefix}-account`}>
          <Input
            value={row.account_code ?? ""}
            onChange={(event) =>
              onChange({ ...row, account_code: event.target.value })
            }
          />
        </Field>
      ) : null}
      {row.kind === "range" ? (
        <div className="mini-grid">
          <Field label="From" htmlFor={`${prefix}-from`}>
            <Input
              value={row.account_from ?? ""}
              onChange={(event) =>
                onChange({ ...row, account_from: event.target.value })
              }
            />
          </Field>
          <Field label="To" htmlFor={`${prefix}-to`}>
            <Input
              value={row.account_to ?? ""}
              onChange={(event) =>
                onChange({ ...row, account_to: event.target.value })
              }
            />
          </Field>
        </div>
      ) : null}
      {row.kind === "formula" ? (
        <Field label="Formula" htmlFor={`${prefix}-formula`}>
          <Input
            value={row.formula ?? ""}
            onChange={(event) =>
              onChange({ ...row, formula: event.target.value })
            }
            placeholder="revenue - expenses"
          />
        </Field>
      ) : null}
      <Switch
        checked={Boolean(row.bold)}
        onChange={(event) => onChange({ ...row, bold: event.target.checked })}
        label="Bold"
      />
    </article>
  );
}

export function CustomReportDesigner({
  token,
  company,
  periods,
  canDesign,
}: Props) {
  const [definitions, setDefinitions] = useState<CustomReportDefinition[]>([]);
  const [selected, setSelected] = useState<CustomReportDefinition | null>(null);
  const [name, setName] = useState("Management statement");
  const [isTemplate, setIsTemplate] = useState(false);
  const [definition, setDefinition] = useState<CustomReportDefinitionData>(() =>
    initialDefinition(periods[0]?.id ?? ""),
  );
  const [result, setResult] = useState<ReportResult | null>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [legacyName, setLegacyName] = useState("Imported GLREP statement");
  const [legacySpec, setLegacySpec] = useState(
    "* Title: Imported balance\nA: [BP1]\n0: 1000\n1: 4000\n2: =",
  );
  const [legacy, setLegacy] = useState<LegacyConversion | null>(null);
  const canRun = useMemo(
    () => company.capabilities.includes("reports.custom.run"),
    [company.capabilities],
  );
  const resolvedDefinition = useMemo<CustomReportDefinitionData>(
    () => ({
      ...definition,
      columns: definition.columns.map((column) =>
        column.kind === "formula"
          ? column
          : {
              ...column,
              period_id: column.period_id || periods[0]?.id || null,
            },
      ),
    }),
    [definition, periods],
  );

  const refresh = useCallback(
    async () =>
      setDefinitions(
        await api<CustomReportDefinition[]>(
          "/custom-reports",
          {},
          token,
          company.id,
        ),
      ),
    [company.id, token],
  );
  useEffect(() => {
    const handle = window.setTimeout(
      () =>
        void refresh().catch((caught: unknown) =>
          setMessage(
            caught instanceof Error
              ? caught.message
              : "Custom reports could not be loaded",
          ),
        ),
      0,
    );
    return () => window.clearTimeout(handle);
  }, [refresh]);

  function choose(item: CustomReportDefinition) {
    setSelected(item);
    setName(item.name);
    setIsTemplate(item.is_template);
    setDefinition(item.definition);
    setResult(null);
    setMessage("");
  }
  function updateColumn(index: number, value: CustomReportColumn) {
    setDefinition((current) => ({
      ...current,
      columns: current.columns.map((item, itemIndex) =>
        itemIndex === index ? value : item,
      ),
    }));
  }
  function updateRow(index: number, value: CustomReportRow) {
    setDefinition((current) => {
      const priorKey = current.rows[index].key;
      return {
        ...current,
        rows: current.rows.map((item, itemIndex) =>
          itemIndex === index ? value : item,
        ),
        sections: current.sections.map((section) => ({
          ...section,
          row_keys: section.row_keys.map((key) =>
            key === priorKey ? value.key : key,
          ),
        })),
      };
    });
  }
  function toggleSectionRow(rowKey: string) {
    setDefinition((current) => {
      const section = current.sections[0] ?? {
        title: "Statement",
        row_keys: [],
      };
      const included = section.row_keys.includes(rowKey);
      return {
        ...current,
        sections: [
          {
            ...section,
            row_keys: included
              ? section.row_keys.filter((key) => key !== rowKey)
              : [...section.row_keys, rowKey],
          },
        ],
      };
    });
  }

  async function preview() {
    setBusy(true);
    setMessage("");
    try {
      setResult(
        await api<ReportResult>(
          "/custom-reports/designer/preview",
          {
            method: "POST",
            body: JSON.stringify({
              definition: resolvedDefinition,
              parameters: {},
            }),
          },
          token,
          company.id,
        ),
      );
      setMessage(
        "Preview calculated with fixed-decimal ledger and budget values.",
      );
    } catch (caught) {
      setMessage(caught instanceof Error ? caught.message : "Preview failed");
    } finally {
      setBusy(false);
    }
  }
  async function save(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      const payload = {
        name,
        definition: resolvedDefinition,
        is_template: isTemplate,
        ...(selected ? { version: selected.version } : {}),
      };
      const saved = await api<CustomReportDefinition>(
        selected ? `/custom-reports/${selected.id}` : "/custom-reports",
        { method: selected ? "PUT" : "POST", body: JSON.stringify(payload) },
        token,
        company.id,
      );
      setSelected(saved);
      setIsTemplate(saved.is_template);
      setDefinition(saved.definition);
      setMessage(`Report saved as version ${saved.version}.`);
      await refresh();
    } catch (caught) {
      setMessage(
        caught instanceof Error ? caught.message : "Report could not be saved",
      );
    } finally {
      setBusy(false);
    }
  }
  async function cloneTemplate() {
    if (!selected) return;
    setBusy(true);
    setMessage("");
    try {
      const clone = await api<CustomReportDefinition>(
        `/custom-reports/${selected.id}/clone`,
        { method: "POST" },
        token,
        company.id,
      );
      await refresh();
      choose(clone);
      setMessage("Working copy created from the reusable template.");
    } catch (caught) {
      setMessage(
        caught instanceof Error
          ? caught.message
          : "Template could not be cloned",
      );
    } finally {
      setBusy(false);
    }
  }
  async function run(format = "json") {
    if (!selected) return;
    setBusy(true);
    setMessage("");
    try {
      if (format === "json")
        setResult(
          await api<ReportResult>(
            `/custom-reports/${selected.id}/run`,
            {
              method: "POST",
              body: JSON.stringify({ parameters: {}, format }),
            },
            token,
            company.id,
          ),
        );
      else {
        const download = await apiDownload(
          `/custom-reports/${selected.id}/run`,
          { parameters: {}, format },
          token,
          company.id,
        );
        const url = URL.createObjectURL(download.blob);
        const anchor = document.createElement("a");
        anchor.href = url;
        anchor.download = download.filename;
        anchor.click();
        URL.revokeObjectURL(url);
      }
      setMessage(
        `${format === "json" ? "Browser" : format.toUpperCase()} report generated and audited.`,
      );
    } catch (caught) {
      setMessage(
        caught instanceof Error ? caught.message : "Report run failed",
      );
    } finally {
      setBusy(false);
    }
  }
  async function inspectLegacy() {
    setBusy(true);
    setMessage("");
    try {
      const converted = await api<LegacyConversion>(
        "/custom-reports/legacy/preview",
        {
          method: "POST",
          body: JSON.stringify({
            name: legacyName,
            spec: legacySpec,
            template: "",
          }),
        },
        token,
        company.id,
      );
      setLegacy(converted);
      setMessage(`Legacy definition classified as ${converted.status}.`);
    } catch (caught) {
      setMessage(
        caught instanceof Error
          ? caught.message
          : "Legacy definition could not be parsed",
      );
    } finally {
      setBusy(false);
    }
  }
  async function importLegacy() {
    setBusy(true);
    try {
      const imported = await api<CustomReportDefinition>(
        "/custom-reports/legacy/import",
        {
          method: "POST",
          body: JSON.stringify({
            name: legacyName,
            spec: legacySpec,
            template: "",
          }),
        },
        token,
        company.id,
      );
      await refresh();
      choose(imported);
      setMessage(
        `Legacy report imported with ${imported.conversion_status} status.`,
      );
    } catch (caught) {
      setMessage(
        caught instanceof Error ? caught.message : "Legacy import failed",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="custom-layout">
      <aside className="report-library">
        <div>
          <p className="eyebrow">REPORT LIBRARY</p>
          <h2>Custom reports</h2>
        </div>
        {canDesign ? (
          <Button
            onClick={() => {
              setSelected(null);
              setName("Untitled statement");
              setIsTemplate(false);
              setDefinition(initialDefinition(periods[0]?.id ?? ""));
              setResult(null);
            }}
          >
            New report
          </Button>
        ) : null}
        <div>
          {definitions.map((item) => (
            <Button
              className={selected?.id === item.id ? "active" : ""}
              key={item.id}
              onClick={() => choose(item)}
            >
              <strong>{item.name}</strong>
              <small>
                {item.is_template ? "template" : item.report_type} · v
                {item.version} · {item.conversion_status}
              </small>
            </Button>
          ))}
        </div>
      </aside>
      <main className="designer-workspace">
        <section className="panel">
          <div className="section-heading">
            <div>
              <p className="eyebrow">SAFE STRUCTURED MODEL</p>
              <h2>Report designer</h2>
            </div>
            <Badge>Decimal formulas only</Badge>
          </div>
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
          <form onSubmit={save}>
            <div className="form-grid">
              <Field
                label="Definition name"
                htmlFor="report-definition-name"
                required
              >
                <Input
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  required
                />
              </Field>
              <Field label="Report title" htmlFor="report-title" required>
                <Input
                  value={definition.title}
                  onChange={(event) =>
                    setDefinition((current) => ({
                      ...current,
                      title: event.target.value,
                    }))
                  }
                  required
                />
              </Field>
              <Field label="Decimal places" htmlFor="report-decimals">
                <Select
                  value={Number(definition.formatting.decimals ?? 2)}
                  onChange={(event) =>
                    setDefinition((current) => ({
                      ...current,
                      formatting: {
                        ...current.formatting,
                        decimals: Number(event.target.value),
                      },
                    }))
                  }
                >
                  {[0, 1, 2, 3, 4, 5, 6].map((value) => (
                    <option value={value} key={value}>
                      {value}
                    </option>
                  ))}
                </Select>
              </Field>
              <Switch
                checked={isTemplate}
                onChange={(event) => setIsTemplate(event.target.checked)}
                label="Reusable template"
              />
            </div>
            {selected?.is_template ? (
              <Button
                type="button"
                onClick={() => void cloneTemplate()}
                disabled={busy}
              >
                Create working copy
              </Button>
            ) : null}
            <div className="designer-heading">
              <h3>Columns</h3>
              <Button
                type="button"
                onClick={() =>
                  setDefinition((current) => ({
                    ...current,
                    columns: [
                      ...current.columns,
                      {
                        key: `column_${current.columns.length + 1}`,
                        label: "New column",
                        kind: "balance",
                        period_id: periods[0]?.id,
                        scope: "period",
                      },
                    ],
                  }))
                }
              >
                Add column
              </Button>
            </div>
            <div className="designer-grid">
              {definition.columns.map((column, index) => (
                <ColumnEditor
                  key={index}
                  column={column}
                  periods={periods}
                  onChange={(value) => updateColumn(index, value)}
                  onRemove={() =>
                    setDefinition((current) => ({
                      ...current,
                      columns: current.columns.filter(
                        (_, itemIndex) => itemIndex !== index,
                      ),
                    }))
                  }
                />
              ))}
            </div>
            <div className="designer-heading">
              <h3>Rows</h3>
              <Button
                type="button"
                onClick={() =>
                  setDefinition((current) => ({
                    ...current,
                    rows: [
                      ...current.rows,
                      {
                        key: `row_${current.rows.length + 1}`,
                        label: "New row",
                        kind: "account",
                        account_code: "",
                      },
                    ],
                  }))
                }
              >
                Add row
              </Button>
            </div>
            <div className="designer-grid">
              {definition.rows.map((row, index) => (
                <RowEditor
                  key={index}
                  row={row}
                  onChange={(value) => updateRow(index, value)}
                  onRemove={() =>
                    setDefinition((current) => ({
                      ...current,
                      rows: current.rows.filter(
                        (_, itemIndex) => itemIndex !== index,
                      ),
                      sections: current.sections
                        .map((section) => ({
                          ...section,
                          row_keys: section.row_keys.filter(
                            (key) => key !== row.key,
                          ),
                        }))
                        .filter((section) => section.row_keys.length),
                    }))
                  }
                />
              ))}
            </div>
            <div className="section-editor">
              <Field label="Section title" htmlFor="report-section-title">
                <Input
                  value={definition.sections[0]?.title ?? ""}
                  onChange={(event) =>
                    setDefinition((current) => ({
                      ...current,
                      sections: [
                        {
                          title: event.target.value,
                          row_keys:
                            current.sections[0]?.row_keys ??
                            current.rows.map((row) => row.key),
                        },
                      ],
                    }))
                  }
                />
              </Field>
              <fieldset>
                <legend>Rows in section</legend>
                {definition.rows.map((row) => (
                  <Checkbox
                    key={row.key}
                    checked={
                      definition.sections[0]?.row_keys.includes(row.key) ??
                      false
                    }
                    onChange={() => toggleSectionRow(row.key)}
                    label={row.label || row.key}
                  />
                ))}
              </fieldset>
            </div>
            <div className="designer-actions">
              <Button
                type="button"
                disabled={busy}
                onClick={() => void preview()}
              >
                Preview draft
              </Button>
              {canDesign ? (
                <Button type="submit" variant="primary" busy={busy}>
                  Save definition
                </Button>
              ) : null}
              {selected && canRun ? (
                <>
                  <Button
                    type="button"
                    disabled={busy}
                    onClick={() => void run()}
                  >
                    Run saved
                  </Button>
                  <Button
                    type="button"
                    disabled={busy}
                    onClick={() => void run("pdf")}
                  >
                    PDF
                  </Button>
                  <Button
                    type="button"
                    disabled={busy}
                    onClick={() => void run("xlsx")}
                  >
                    Excel
                  </Button>
                </>
              ) : null}
            </div>
          </form>
        </section>
        {result ? (
          <section className="panel custom-preview">
            <div className="section-heading">
              <div>
                <p className="eyebrow">MATRIX PREVIEW</p>
                <h2>{result.title}</h2>
              </div>
              <Badge tone="success">{result.rows.length} rows</Badge>
            </div>
            <p className="digest">
              Digest · <DigestValue value={result.digest} />
            </p>
            <div className="table-wrap">
              <table>
                <caption className="ds-visually-hidden">
                  {result.title} custom report preview
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
                          {row[column] == null || row[column] === "" ? (
                            ""
                          ) : column === "label" || column === "key" ? (
                            String(row[column] ?? "")
                          ) : (
                            <AmountCell
                              value={String(row[column] ?? "")}
                              currency={company.base_currency_code}
                            />
                          )}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        ) : null}
        {canDesign ? (
          <section className="panel legacy-import">
            <div>
              <p className="eyebrow">ISOLATED COMPATIBILITY</p>
              <h2>Legacy GLREP conversion</h2>
            </div>
            <Field label="Definition name" htmlFor="legacy-report-name">
              <Input
                value={legacyName}
                onChange={(event) => setLegacyName(event.target.value)}
              />
            </Field>
            <Field
              label="Legacy matrix specification"
              htmlFor="legacy-report-spec"
            >
              <Textarea
                mono
                rows={8}
                value={legacySpec}
                onChange={(event) => {
                  setLegacySpec(event.target.value);
                  setLegacy(null);
                }}
              />
            </Field>
            <div className="button-row">
              <Button busy={busy} onClick={() => void inspectLegacy()}>
                Analyze safely
              </Button>
              <Button
                variant="primary"
                disabled={busy || !legacy}
                onClick={() => void importLegacy()}
              >
                Import with status
              </Button>
            </div>
            {legacy ? (
              <div className={`conversion ${legacy.status}`}>
                <StatusPill status={legacy.status} />
                {legacy.warnings.length ? (
                  <ul>
                    {legacy.warnings.map((warning) => (
                      <li key={warning}>{warning}</li>
                    ))}
                  </ul>
                ) : (
                  <p>No unmapped constructs detected.</p>
                )}
              </div>
            ) : null}
          </section>
        ) : null}
      </main>
    </div>
  );
}
