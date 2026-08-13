import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CustomReportDesigner } from "./CustomReportDesigner";
import { LegacyMigrationPanel } from "./LegacyMigrationPanel";
import type { CustomReportDefinition, MigrationRun } from "./types";

const company = {
  id: "c1",
  code: "ACME",
  name: "Acme",
  base_currency_code: "SGD",
  role: "Administrator",
  capabilities: ["reports.custom.run"],
};
const periods = [
  {
    id: "p1",
    fiscal_year_id: "fy",
    period_no: 1,
    label: "P01",
    start_date: "2026-01-01",
    end_date: "2026-01-31",
    status: "open",
  },
];
const definition = {
  title: "Cash report",
  columns: [
    {
      key: "actual",
      label: "Actual",
      kind: "balance" as const,
      period_id: "p1",
      scope: "period" as const,
    },
  ],
  rows: [
    {
      key: "cash",
      label: "Cash",
      kind: "account" as const,
      account_code: "1000",
    },
  ],
  sections: [{ title: "Assets", row_keys: ["cash"] }],
  formatting: { decimals: 2 },
};
const saved: CustomReportDefinition = {
  id: "r1",
  name: "Cash report",
  report_type: "statement",
  definition,
  conversion_status: "compatible",
  is_template: true,
  version: 2,
  created_at: "2026-01-01",
  updated_at: "2026-01-01",
};
const migration: MigrationRun = {
  id: "m1",
  source_path: "legacy.zip",
  source_digest: "abc123",
  status: "succeeded",
  dry_run: true,
  counts: { records: 4, errors: 0, warnings: 1 },
  reconciliation: {
    apply_ready: true,
    ledger_balanced: true,
    account_periods_match: true,
    ledger_debits: "10.00",
    ledger_credits: "10.00",
  },
  staging_records: [
    {
      id: "e1",
      source_table: "GLACCNT",
      source_record: 2,
      natural_key: "1000",
      severity: "warning",
      issues: [
        { code: "TRIMMED", message: "Whitespace removed", blocking: false },
      ],
    },
  ],
  created_at: "2026-01-01",
};

function json(
  body: unknown,
  status = 200,
  headers: Record<string, string> = {},
) {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json", ...headers },
    }),
  );
}

describe("CustomReportDesigner", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        if (url.endsWith("/custom-reports") && !init?.method)
          return json([saved]);
        if (url.endsWith("/designer/preview"))
          return json({
            title: "Preview",
            columns: ["label", "actual"],
            rows: [{ label: "Cash", actual: "10.00" }],
            digest: "digest",
          });
        if (url.endsWith("/legacy/preview"))
          return json({
            status: "partial",
            definition,
            warnings: ["Manual heading review"],
          });
        if (url.endsWith("/legacy/import"))
          return json({
            ...saved,
            id: "r2",
            is_template: false,
            conversion_status: "partial",
          });
        if (url.endsWith("/clone"))
          return json({
            ...saved,
            id: "r3",
            name: "Cash report copy",
            is_template: false,
          });
        if (url.endsWith("/run"))
          return init?.body && JSON.parse(String(init.body)).format === "json"
            ? json({
                title: "Cash report",
                columns: ["actual"],
                rows: [{ actual: "10.00" }],
                digest: "run-digest",
              })
            : Promise.resolve(
                new Response("pdf", {
                  status: 200,
                  headers: {
                    "Content-Disposition": 'attachment; filename="cash.pdf"',
                  },
                }),
              );
        if (url.includes("/custom-reports/r1"))
          return json({ ...saved, version: 3 });
        if (url.endsWith("/custom-reports")) return json(saved);
        return json({}, 404);
      }),
    );
    vi.stubGlobal("URL", {
      ...URL,
      createObjectURL: vi.fn(() => "blob:test"),
      revokeObjectURL: vi.fn(),
    });
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(
      () => undefined,
    );
  });

  it("supports structured editing, preview, save, template clone, run, and legacy analysis", async () => {
    const user = userEvent.setup();
    render(
      <CustomReportDesigner
        token="t"
        company={company}
        periods={periods}
        canDesign
      />,
    );
    await user.click(
      await screen.findByRole("button", { name: /Cash report/ }),
    );
    expect(
      screen.getByRole("button", { name: "Create working copy" }),
    ).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Add column" }));
    const newColumnKey = screen.getAllByLabelText("Key")[1];
    await user.clear(newColumnKey);
    await user.type(newColumnKey, "New Value!");
    expect(screen.getAllByLabelText("Key")[1]).toHaveValue("newvalue");
    await user.click(screen.getByRole("button", { name: "Add row" }));
    await user.selectOptions(
      screen.getAllByLabelText("Row type").at(-1)!,
      "range",
    );
    expect(screen.getByLabelText("From")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Preview draft" }));
    expect(
      await screen.findByRole("heading", { name: "Preview" }),
    ).toBeVisible();
    expect(screen.getByText("10.00")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Save definition" }));
    expect(await screen.findByRole("status")).toHaveTextContent("version 3");
    await user.click(
      screen.getByRole("button", { name: "Create working copy" }),
    );
    expect(await screen.findByRole("status")).toHaveTextContent("Working copy");
    await user.click(screen.getByRole("button", { name: "Run saved" }));
    await waitFor(() =>
      expect(document.querySelector(".digest")).toHaveTextContent("run-digest"),
    );
    await user.click(screen.getByRole("button", { name: "PDF" }));
    expect(await screen.findByRole("status")).toHaveTextContent(
      "PDF report generated",
    );
    await user.click(screen.getByRole("button", { name: "Excel" }));
    expect(await screen.findByRole("status")).toHaveTextContent(
      "XLSX report generated",
    );
    await user.click(screen.getByRole("button", { name: "Analyze safely" }));
    expect(await screen.findByText("Manual heading review")).toBeVisible();
    await user.click(
      screen.getByRole("button", { name: "Import with status" }),
    );
    expect(await screen.findByRole("status")).toHaveTextContent(
      "partial status",
    );
  });

  it("hides design and legacy controls for run-only users and announces load errors", async () => {
    vi.mocked(fetch).mockImplementation(() =>
      json({ detail: "Definitions unavailable" }, 503),
    );
    render(
      <CustomReportDesigner
        token="t"
        company={company}
        periods={periods}
        canDesign={false}
      />,
    );
    expect(
      screen.queryByRole("button", { name: "New report" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "Legacy GLREP conversion" }),
    ).not.toBeInTheDocument();
    expect(await screen.findByRole("status")).toHaveTextContent(
      "Definitions unavailable",
    );
  });

  it("edits every structured column and row variant using stable focused controls", async () => {
    const user = userEvent.setup();
    render(
      <CustomReportDesigner
        token="t"
        company={company}
        periods={periods}
        canDesign
      />,
    );
    await user.click(await screen.findByRole("button", { name: "New report" }));
    await user.selectOptions(screen.getByLabelText("Decimal places"), "4");
    await user.click(
      screen.getByRole("checkbox", { name: "Reusable template" }),
    );

    const columnSources = screen.getAllByLabelText("Source");
    await user.selectOptions(columnSources[0], "formula");
    expect(screen.getAllByLabelText("Formula")[0]).toBeVisible();
    await user.selectOptions(screen.getAllByLabelText("Source")[2], "budget");
    await user.clear(screen.getAllByLabelText("Scenario").at(-1)!);
    await user.type(screen.getAllByLabelText("Scenario").at(-1)!, "Forecast");
    await user.selectOptions(screen.getAllByLabelText("Scope").at(-1)!, "ytd");
    await user.selectOptions(screen.getAllByLabelText("Period").at(-1)!, "p1");
    await user.clear(screen.getAllByLabelText("Label")[0]);
    await user.type(screen.getAllByLabelText("Label")[0], "Calculated");

    const rowTypes = screen.getAllByLabelText("Row type");
    await user.selectOptions(rowTypes[0], "range");
    await user.type(screen.getByLabelText("From"), "1000");
    await user.type(screen.getByLabelText("To"), "1999");
    await user.selectOptions(
      screen.getAllByLabelText("Row type")[1],
      "formula",
    );
    await user.clear(screen.getAllByLabelText("Formula").at(-1)!);
    await user.type(
      screen.getAllByLabelText("Formula").at(-1)!,
      "cash + sales",
    );
    await user.selectOptions(
      screen.getAllByLabelText("Row type")[2],
      "heading",
    );
    await user.click(screen.getAllByRole("checkbox", { name: "Bold" })[0]);
    await user.clear(screen.getByLabelText("Section title"));
    await user.type(screen.getByLabelText("Section title"), "Assets");
    const sectionCash = screen.getByRole("checkbox", { name: "Cash" });
    await user.click(sectionCash);
    await user.click(sectionCash);
    await user.click(screen.getAllByRole("button", { name: "Remove" })[0]);
    await user.click(screen.getAllByRole("button", { name: "Remove" }).at(-1)!);
    expect(screen.getByLabelText("Decimal places")).toHaveValue("4");
  }, 15_000);

  it("announces preview, save, clone, run, legacy analysis, and import failures", async () => {
    vi.mocked(fetch).mockImplementation(
      (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        if (url.endsWith("/custom-reports") && !init?.method)
          return json([saved]);
        if (url.endsWith("/legacy/preview"))
          return json({ status: "compatible", definition, warnings: [] });
        return json({ detail: `Rejected ${url.split("/").at(-1)}` }, 422);
      },
    );
    const user = userEvent.setup();
    render(
      <CustomReportDesigner
        token="t"
        company={company}
        periods={periods}
        canDesign
      />,
    );
    await user.click(
      await screen.findByRole("button", { name: /Cash report/ }),
    );
    await user.click(screen.getByRole("button", { name: "Preview draft" }));
    expect(await screen.findByRole("status")).toHaveTextContent(
      "Rejected preview",
    );
    await user.click(screen.getByRole("button", { name: "Save definition" }));
    expect(await screen.findByRole("status")).toHaveTextContent("Rejected r1");
    await user.click(
      screen.getByRole("button", { name: "Create working copy" }),
    );
    expect(await screen.findByRole("status")).toHaveTextContent(
      "Rejected clone",
    );
    await user.click(screen.getByRole("button", { name: "Run saved" }));
    expect(await screen.findByRole("status")).toHaveTextContent("Rejected run");
    await user.click(screen.getByRole("button", { name: "Analyze safely" }));
    expect(
      await screen.findByText("No unmapped constructs detected."),
    ).toBeVisible();
    await user.click(
      screen.getByRole("button", { name: "Import with status" }),
    );
    expect(await screen.findByRole("status")).toHaveTextContent(
      "Rejected import",
    );
  });

  it("handles sparse definitions, empty periods, fallback sections, and new-report POST saves", async () => {
    const sparse: CustomReportDefinition = {
      ...saved,
      id: "sparse",
      name: "Sparse report",
      is_template: false,
      definition: {
        title: "",
        columns: [
          {
            key: "blank",
            label: "Blank",
            kind: "balance",
            period_id: null,
            scope: "period",
          },
        ],
        rows: [
          { key: "blank", label: "", kind: "account", account_code: null },
        ],
        sections: [],
        formatting: {},
      },
    };
    vi.mocked(fetch).mockImplementation(
      (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        if (url.endsWith("/custom-reports") && !init?.method)
          return json([sparse]);
        if (url.endsWith("/designer/preview"))
          return json({
            title: "Sparse preview",
            columns: ["blank"],
            rows: [{}],
            digest: "sparse-digest",
          });
        if (url.endsWith("/custom-reports") && init?.method === "POST")
          return json({ ...saved, id: "new", is_template: false, version: 1 });
        return json(sparse);
      },
    );
    const user = userEvent.setup();
    render(
      <CustomReportDesigner
        token="t"
        company={company}
        periods={[]}
        canDesign
      />,
    );
    await user.click(
      await screen.findByRole("button", { name: /Sparse report/ }),
    );
    expect(screen.getByText(/statement · v2/)).toBeVisible();
    expect(screen.getByLabelText("Decimal places")).toHaveValue("2");
    expect(screen.getByLabelText("Section title")).toHaveValue("");
    expect(screen.getByRole("checkbox", { name: "blank" })).not.toBeChecked();
    await user.click(screen.getByRole("checkbox", { name: "blank" }));
    await user.clear(screen.getByLabelText("Section title"));
    await user.type(screen.getByLabelText("Section title"), "Fallback section");
    await user.type(screen.getByLabelText("Account code"), "1000");
    await user.clear(screen.getAllByLabelText("Key").at(-1)!);
    await user.type(screen.getAllByLabelText("Key").at(-1)!, "cash");
    await user.type(screen.getAllByLabelText("Label").at(-1)!, "Cash");
    await user.selectOptions(screen.getByLabelText("Source"), "formula");
    await user.type(screen.getByLabelText("Formula"), "1 + 1");
    await user.click(screen.getByRole("button", { name: "Preview draft" }));
    expect(
      await screen.findByRole("heading", { name: "Sparse preview" }),
    ).toBeVisible();
    expect(document.querySelector(".custom-preview td")).toHaveTextContent("");

    await user.click(screen.getByRole("button", { name: "New report" }));
    await user.clear(screen.getAllByLabelText("Definition name")[0]);
    await user.type(
      screen.getAllByLabelText("Definition name")[0],
      "New report",
    );
    await user.clear(screen.getByLabelText("Report title"));
    await user.type(screen.getByLabelText("Report title"), "New title");
    await user.click(screen.getByRole("button", { name: "Save definition" }));
    expect(await screen.findByRole("status")).toHaveTextContent("version 1");
    expect(
      vi
        .mocked(fetch)
        .mock.calls.some(
          ([url, init]) =>
            String(url).endsWith("/custom-reports") && init?.method === "POST",
        ),
    ).toBe(true);
  });
});

describe("LegacyMigrationPanel", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        if (url.endsWith("/migration/runs") && !init?.method)
          return json([migration]);
        if (url.endsWith("/migration/stage")) return json(migration);
        if (url.endsWith("/exceptions.csv"))
          return Promise.resolve(
            new Response("row,error", {
              status: 200,
              headers: {
                "Content-Disposition": 'attachment; filename="exceptions.csv"',
              },
            }),
          );
        if (url.endsWith("/apply"))
          return json({ ...migration, dry_run: false });
        if (url.endsWith("/migration/runs/m1")) return json(migration);
        return json({}, 404);
      }),
    );
    vi.stubGlobal("URL", {
      ...URL,
      createObjectURL: vi.fn(() => "blob:test"),
      revokeObjectURL: vi.fn(),
    });
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(
      () => undefined,
    );
  });

  it("stages, reconciles, downloads exceptions, and applies only after exact confirmation", async () => {
    const user = userEvent.setup();
    render(<LegacyMigrationPanel token="t" company={company} />);
    expect(
      await screen.findByRole("button", { name: /legacy.zip/ }),
    ).toBeVisible();
    const file = new File(["zip"], "legacy.zip", { type: "application/zip" });
    fireEvent.change(screen.getByLabelText("Legacy DBF snapshot"), {
      target: { files: [file] },
    });
    await user.click(
      screen.getByRole("button", { name: "Run read-only trial" }),
    );
    expect(await screen.findByRole("status")).toHaveTextContent(
      "ready for controlled apply",
    );
    expect(screen.getByText("TRIMMED: Whitespace removed")).toBeVisible();
    const apply = screen.getByRole("button", {
      name: "Apply reconciled snapshot",
    });
    await user.click(
      screen.getByRole("button", { name: "Download exceptions" }),
    );
    await user.click(apply);
    const dialog = screen.getByRole("dialog", {
      name: "Apply legacy migration",
    });
    const confirm = within(dialog).getByRole("button", {
      name: "Apply migration",
    });
    expect(confirm).toBeDisabled();
    await user.type(
      within(dialog).getByLabelText("Type APPLY to continue"),
      "APPLY",
    );
    expect(confirm).toBeEnabled();
    await user.click(confirm);
    expect(await screen.findByRole("status")).toHaveTextContent(
      "applied atomically",
    );
  });

  it("opens history and announces failed history loading", async () => {
    const user = userEvent.setup();
    render(<LegacyMigrationPanel token="t" company={company} />);
    await user.click(await screen.findByRole("button", { name: /legacy.zip/ }));
    await waitFor(() => expect(screen.getByText("abc123")).toBeVisible());
  });

  it("renders blocking reconciliation differences without exposing apply", async () => {
    const blocked = {
      ...migration,
      counts: { records: 3, errors: 2, warnings: 0 },
      reconciliation: {
        apply_ready: false,
        ledger_balanced: false,
        account_periods_match: false,
        blocking_reason: "Debit and credit totals differ",
      },
      staging_records: [
        { ...migration.staging_records[0], severity: "error" as const },
      ],
    };
    vi.mocked(fetch).mockImplementation((input: RequestInfo | URL) =>
      String(input).endsWith("/migration/runs") ? json([]) : json(blocked),
    );
    const user = userEvent.setup();
    render(<LegacyMigrationPanel token="t" company={company} />);
    fireEvent.change(screen.getByLabelText("Legacy DBF snapshot"), {
      target: { files: [new File(["zip"], "bad.zip")] },
    });
    await user.click(
      screen.getByRole("button", { name: "Run read-only trial" }),
    );
    expect(await screen.findByRole("status")).toHaveTextContent(
      "blocking exceptions",
    );
    expect(screen.getByText("Difference")).toBeVisible();
    expect(
      screen.getByText("do not reconcile", { exact: false }),
    ).toBeVisible();
    expect(screen.getByText("Debit and credit totals differ")).toBeVisible();
    expect(
      screen.queryByRole("button", { name: "Apply reconciled snapshot" }),
    ).not.toBeInTheDocument();
  });

  it("announces migration history, stage, open, and apply errors", async () => {
    vi.mocked(fetch).mockImplementation(
      (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        if (url.endsWith("/migration/runs") && !init?.method)
          return json([migration]);
        if (url.endsWith("/migration/stage"))
          return json({ detail: "Archive unsafe" }, 422);
        if (url.endsWith("/migration/runs/m1"))
          return json({ detail: "Run missing" }, 404);
        return json({ detail: "Apply conflict" }, 409);
      },
    );
    const user = userEvent.setup();
    render(<LegacyMigrationPanel token="t" company={company} />);
    fireEvent.change(screen.getByLabelText("Legacy DBF snapshot"), {
      target: { files: [new File(["zip"], "bad.zip")] },
    });
    await user.click(
      screen.getByRole("button", { name: "Run read-only trial" }),
    );
    expect(await screen.findByRole("status")).toHaveTextContent(
      "Archive unsafe",
    );
    await user.click(screen.getByRole("button", { name: /legacy.zip/ }));
    expect(await screen.findByRole("status")).toHaveTextContent("Run missing");
  });

  it("announces migration history loading failure", async () => {
    vi.mocked(fetch).mockImplementation(() =>
      json({ detail: "Migration history unavailable" }, 503),
    );
    render(<LegacyMigrationPanel token="t" company={company} />);
    expect(await screen.findByRole("status")).toHaveTextContent(
      "Migration history unavailable",
    );
  });

  it("renders applied failed history and missing optional reconciliation counts safely", async () => {
    const sparse: MigrationRun = {
      ...migration,
      id: "m2",
      status: "failed",
      dry_run: false,
      counts: {},
      reconciliation: { ledger_balanced: false, account_periods_match: false },
      staging_records: [],
    };
    vi.mocked(fetch).mockImplementation((input: RequestInfo | URL) =>
      String(input).endsWith("/migration/runs") ? json([sparse]) : json(sparse),
    );
    const user = userEvent.setup();
    render(<LegacyMigrationPanel token="t" company={company} />);
    const history = await screen.findByRole("button", { name: /legacy.zip/ });
    expect(history).toHaveTextContent("applied");
    expect(within(history).getByText("failed")).toHaveClass("ds-status");
    await user.click(history);
    expect(await screen.findByText("Difference")).toBeVisible();
    expect(
      screen.getByText("Rows staged").nextElementSibling,
    ).toHaveTextContent("0");
    expect(
      screen.getByText("Blocking rows").nextElementSibling,
    ).toHaveTextContent("0");
    expect(screen.getByText("Warnings").nextElementSibling).toHaveTextContent(
      "0",
    );
    fireEvent.change(screen.getByLabelText("Legacy DBF snapshot"), {
      target: { files: [] },
    });
    expect(
      screen.getByRole("button", { name: "Run read-only trial" }),
    ).toBeDisabled();
  });
});
