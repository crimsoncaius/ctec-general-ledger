import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";

const capabilities = [
  "accounts.view",
  "accounts.create",
  "accounts.update",
  "accounts.import",
  "journals.view",
  "journals.create",
  "journals.update",
  "journals.delete",
  "journals.validate",
  "journals.approve",
  "journals.post",
  "journals.reverse",
  "journals.import",
  "fiscal.manage",
  "fiscal.close",
  "budgets.manage",
  "reports.run",
  "reports.custom.run",
  "reports.custom.design",
  "users.manage",
  "company.manage",
  "preferences.manage",
  "administration.organize",
  "audit.view",
  "migration.run",
  "integrity.run",
];
const company = {
  id: "c1",
  code: "ACME",
  name: "Acme Trading",
  base_currency_code: "SGD",
  role: "Administrator",
  capabilities,
};
const accounts = [
  {
    id: "a1",
    code: "1000",
    name: "Cash",
    account_type: "balance_sheet",
    currency_code: "SGD",
    postable: true,
    active: true,
  },
  {
    id: "a2",
    code: "4000",
    name: "Revenue",
    account_type: "revenue_expense",
    currency_code: "SGD",
    postable: true,
    active: true,
  },
];
const periods = [
  {
    id: "p1",
    fiscal_year_id: "fy1",
    period_no: 1,
    label: "P01",
    start_date: "2026-01-01",
    end_date: "2026-12-31",
    status: "open",
  },
  {
    id: "p2",
    fiscal_year_id: "fy2",
    period_no: 1,
    label: "P01 FY27",
    start_date: "2027-01-01",
    end_date: "2027-01-31",
    status: "open",
  },
];
const line = (id: string, account: string, debit: string, credit: string) => ({
  id,
  line_no: 1,
  account_id: account,
  description: "",
  currency_code: "SGD",
  exchange_rate: "1",
  debit_original: debit,
  credit_original: credit,
  debit_base: debit,
  credit_base: credit,
});
const entry = (id: string, status: string) => ({
  id,
  entry_no: `JE-${id}`,
  entry_date: "2026-01-01",
  posting_date: "2026-01-01",
  fiscal_period_id: "p1",
  reference: "WEB",
  description: `${status} entry`,
  status,
  reversal_of_id: null,
  lines: [
    line(`${id}-1`, "a1", "10.00", "0"),
    line(`${id}-2`, "a2", "0", "10.00"),
  ],
});
const batches = [
  {
    id: "b1",
    batch_no: "B-DRAFT",
    description: "",
    status: "draft",
    created_at: "2026-01-01",
    entries: [entry("e1", "draft"), entry("e1b", "draft")],
  },
  {
    id: "b2",
    batch_no: "B-VALID",
    description: "Validated batch",
    status: "validated",
    created_at: "2026-01-01",
    entries: [entry("e2", "validated")],
  },
  {
    id: "b3",
    batch_no: "B-APPROVED",
    description: "Approved batch",
    status: "approved",
    created_at: "2026-01-01",
    entries: [entry("e3", "approved")],
  },
  {
    id: "b4",
    batch_no: "B-POSTED",
    description: "Posted batch",
    status: "posted",
    created_at: "2026-01-01",
    entries: [
      entry("e4", "posted"),
      { ...entry("e5", "posted"), reversal_of_id: "e4" },
    ],
  },
];

function json(body: unknown, status = 200) {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" },
    }),
  );
}

function installRouter() {
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? "GET";
      if (url.endsWith("/auth/token")) return json({ access_token: "token" });
      if (url.endsWith("/auth/me"))
        return json({
          id: "u1",
          email: "admin@example.com",
          display_name: "Demo Administrator",
          companies: [company],
        });
      if (url.endsWith("/accounts") && method === "GET") return json(accounts);
      if (url.endsWith("/fiscal/periods")) return json(periods);
      if (url.endsWith("/fiscal/years"))
        return json([
          {
            id: "fy1",
            label: "FY2026",
            start_date: "2026-01-01",
            end_date: "2026-12-31",
            closed_at: null,
          },
          {
            id: "fy2",
            label: "FY2027",
            start_date: "2027-01-01",
            end_date: "2027-12-31",
            closed_at: null,
          },
        ]);
      if (url.endsWith("/journals") && method === "GET") return json(batches);
      if (url.endsWith("/budgets") && method === "GET")
        return json([
          {
            id: "bu1",
            fiscal_period_id: "p1",
            account_id: "a2",
            scenario: "Current",
            currency_code: "SGD",
            amount: "25.00",
          },
        ]);
      if (url.endsWith("/reports/runs"))
        return json([
          {
            id: "run1",
            report_type: "trial_balance",
            parameters: {},
            format: "json",
            digest: "old",
            created_at: "2026-01-01",
          },
        ]);
      if (url.endsWith("/ledger/integrity")) return json({ ok: true });
      if (url.includes("close-preview"))
        return json({
          balanced: true,
          profit_loss: "20.00",
          closing_lines: 2,
          opening_lines: 2,
        });
      if (url.endsWith("/reports/run"))
        return json({
          title: "Trial balance",
          columns: ["account", "balance"],
          rows: [{ account: "Cash", balance: "10.00" }],
          digest: "digest-1",
        });
      if (url.endsWith("/reports/runs/run1/reproduce"))
        return json({
          title: "Reproduced trial balance",
          columns: ["account"],
          rows: [{ account: "Cash" }],
          digest: "digest-2",
        });
      if (url.endsWith("/custom-reports")) return json([]);
      if (url.endsWith("/administration/company"))
        return json({
          name: "Acme Trading",
          timezone: "Asia/Singapore",
          rounding_places: 2,
          use_bankers_rounding: true,
        });
      if (url.endsWith("/administration/roles") && method === "POST")
        return json({
          id: "r2",
          name: "Read-only analyst",
          description: "",
          system: false,
          active: true,
        });
      if (url.endsWith("/administration/roles"))
        return json([
          {
            id: "r1",
            name: "Administrator",
            description: "Admin",
            system: true,
            active: true,
          },
        ]);
      if (url.endsWith("/administration/permissions")) return json([]);
      if (url.endsWith("/administration/users") && method === "POST")
        return json({});
      if (url.endsWith("/administration/users"))
        return json([
          {
            user_id: "u1",
            email: "admin@example.com",
            display_name: "Demo Administrator",
            role_id: "r1",
            role_name: "Administrator",
            active: true,
          },
        ]);
      if (url.includes("/administration/audit"))
        return json([
          {
            id: "au1",
            action: "journal.post",
            entity_type: "journal",
            entity_id: "b4",
            occurred_at: "2026-01-01",
          },
        ]);
      if (url.endsWith("/administration/operations")) return json([]);
      if (url.endsWith("/migration/runs")) return json([]);
      if (url.includes("/imports/") && url.endsWith("/preview"))
        return json({ rows: 2, valid: 2, entries: 2, errors: [] });
      if (url.includes("/imports/accounts/apply"))
        return json({ rows: 2, valid: 2, errors: [], created: 2, updated: 0 });
      if (url.includes("/imports/journals/apply"))
        return json({
          rows: 2,
          entries: 2,
          errors: [],
          batch_id: "B-IMPORTED",
        });
      if (url.endsWith("/journals/bulk"))
        return json({ succeeded: ["b1"], failed: [] });
      return json({}, method === "DELETE" ? 204 : 200);
    }),
  );
}

async function signIn() {
  const user = userEvent.setup();
  render(<App />);
  await user.click(screen.getByRole("button", { name: "Sign in" }));
  await screen.findByRole("heading", { name: "Acme Trading" });
  return user;
}

describe("full workspace behavior", () => {
  beforeEach(() => installRouter());

  it("navigates all capability-controlled workspaces with keyboard and preserves accessible focus", async () => {
    const user = await signIn();
    const nav = screen.getByRole("navigation", { name: "Primary" });
    for (const name of [
      "overview",
      "accounts",
      "journals",
      "inquiry",
      "fiscal",
      "planning",
      "reports",
      "designer",
      "admin",
    ]) {
      expect(within(nav).getByRole("button", { name })).toBeVisible();
    }
    await user.keyboard("{Alt>}j{/Alt}");
    expect(
      await screen.findByRole("heading", { name: "Balanced journal" }),
    ).toBeVisible();
    await user.tab();
    expect(document.activeElement).not.toBe(document.body);
    await user.keyboard("{Alt>}i{/Alt}");
    expect(
      await screen.findByRole("heading", { name: "Posted journal inquiry" }),
    ).toBeVisible();
    await user.keyboard("{Alt>}r{/Alt}");
    expect(
      await screen.findByRole("heading", {
        name: "Standard reports",
        level: 1,
      }),
    ).toBeVisible();
  });

  it("runs overview, journal workflow, inquiry, planning, and reporting actions", async () => {
    const user = await signIn();
    await user.click(screen.getByRole("button", { name: "Run integrity" }));
    expect(await screen.findByRole("status")).toHaveTextContent("reconcile");

    await user.click(screen.getByRole("button", { name: "journals" }));
    await user.click(
      screen.getByRole("button", { name: "Create draft batch" }),
    );
    await waitFor(() =>
      expect(
        vi
          .mocked(fetch)
          .mock.calls.some(
            ([url, init]) =>
              String(url).endsWith("/journals") && init?.method === "POST",
          ),
      ).toBe(true),
    );
    await user.clear(screen.getByLabelText("Draft description for B-DRAFT"));
    await user.type(
      screen.getByLabelText("Draft description for B-DRAFT"),
      "Corrected draft",
    );
    await user.click(screen.getByRole("button", { name: "Save draft" }));
    await user.click(screen.getByRole("button", { name: "Copy" }));
    await user.click(screen.getByRole("button", { name: "Delete draft" }));
    await user.click(
      within(
        screen.getByRole("dialog", { name: "Delete draft journal" }),
      ).getByRole("button", { name: "Delete draft" }),
    );
    await user.click(screen.getByRole("button", { name: "Validate" }));
    await user.click(screen.getByRole("button", { name: "Approve" }));
    await user.click(screen.getByRole("button", { name: "Post" }));
    await user.click(
      within(
        screen.getByRole("dialog", { name: "Post approved journal batch" }),
      ).getByRole("button", { name: "Post batch" }),
    );
    await user.click(screen.getByLabelText("Mark B-DRAFT"));
    await user.click(screen.getByRole("button", { name: "Bulk validate" }));

    await user.click(screen.getByRole("button", { name: "inquiry" }));
    await user.click(screen.getByRole("button", { name: "Reverse" }));
    expect(screen.getByLabelText("Reversal reason")).toBeVisible();
    await user.click(
      screen.getByRole("button", { name: "Post linked reversal" }),
    );
    await waitFor(() =>
      expect(
        vi
          .mocked(fetch)
          .mock.calls.some(([url]) => String(url).includes("/reverse")),
      ).toBe(true),
    );

    await user.click(screen.getByRole("button", { name: "planning" }));
    expect(screen.getByRole("heading", { name: "Budgets" })).toBeVisible();
    await user.clear(screen.getByLabelText(/Budget amount/));
    await user.type(screen.getByLabelText(/Budget amount/), "50.25");
    await user.click(
      screen.getByRole("button", { name: "Save budget version" }),
    );
    expect(
      (
        await screen.findByText("Budget version saved with audit history.")
      ).closest('[role="status"]'),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Preview close" }));
    expect(await screen.findByText("Reconciled")).toBeVisible();
    await user.click(
      screen.getByRole("button", { name: "Execute non-destructive close" }),
    );
    await user.click(
      within(
        screen.getByRole("dialog", { name: "Execute fiscal close" }),
      ).getByRole("button", { name: "Execute close" }),
    );
    expect(
      (await screen.findByText(/Fiscal close posted/)).closest(
        '[role="status"]',
      ),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "reports" }));
    expect(
      screen.getByRole("heading", { name: "Select a report" }),
    ).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Run report" }));
    expect(
      await screen.findByRole("heading", { name: "Trial balance" }),
    ).toBeVisible();
    await user.click(screen.getByRole("button", { name: /trial balance/ }));
    expect(
      await screen.findByRole("heading", { name: "Reproduced trial balance" }),
    ).toBeVisible();
  });

  it("renders fiscal and administration data, capability semantics, and signs out", async () => {
    const user = await signIn();
    await user.click(screen.getByRole("button", { name: "fiscal" }));
    expect(screen.getByRole("heading", { name: "2 periods" })).toBeVisible();
    expect(
      screen.getByRole("heading", { name: "New fiscal year" }),
    ).toBeVisible();
    await user.click(screen.getByRole("button", { name: "admin" }));
    expect(
      await screen.findByRole("heading", { name: "Administration" }),
    ).toBeVisible();
    expect(
      await screen.findByRole("heading", { name: "Users and roles" }),
    ).toBeVisible();
    expect(
      screen.getByRole("heading", { name: "Audit history" }),
    ).toBeVisible();
    expect(screen.getByRole("heading", { name: "Operations" })).toBeVisible();
    expect(
      screen.getByRole("heading", { name: "Legacy migration" }),
    ).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Save display" }));
    expect(await screen.findByRole("status")).toHaveTextContent(
      "Display preference saved",
    );
    await user.click(screen.getByRole("button", { name: "Sign out" }));
    expect(screen.getByRole("heading", { name: "Welcome back" })).toBeVisible();
  });

  it("shows a company-free state and blocks privileged navigation for a restricted user", async () => {
    vi.mocked(fetch).mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/auth/token")) return json({ access_token: "token" });
      if (url.endsWith("/auth/me"))
        return json({
          id: "u2",
          email: "none@example.com",
          display_name: "No Company",
          companies: [],
        });
      return json([]);
    });
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole("button", { name: "Sign in" }));
    expect(
      await screen.findByRole("heading", { name: "No company access" }),
    ).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Sign out" }));
    expect(screen.getByRole("button", { name: "Sign in" })).toBeVisible();
  });

  it("hides privileged pages and mutation controls for a restricted company member", async () => {
    const base = vi.mocked(fetch).getMockImplementation()!;
    vi.mocked(fetch).mockImplementation(
      (input: RequestInfo | URL, init?: RequestInit) =>
        String(input).endsWith("/auth/me")
          ? json({
              id: "u3",
              email: "viewer@example.com",
              display_name: "Read Only",
              companies: [{ ...company, role: "Viewer", capabilities: [] }],
            })
          : base(input, init),
    );
    const user = await signIn();
    const nav = screen.getByRole("navigation", { name: "Primary" });
    expect(
      within(nav).queryByRole("button", { name: "planning" }),
    ).not.toBeInTheDocument();
    expect(
      within(nav).queryByRole("button", { name: "reports" }),
    ).not.toBeInTheDocument();
    expect(
      within(nav).queryByRole("button", { name: "designer" }),
    ).not.toBeInTheDocument();
    expect(
      within(nav).queryByRole("button", { name: "admin" }),
    ).not.toBeInTheDocument();
    await user.click(within(nav).getByRole("button", { name: "accounts" }));
    expect(
      screen.queryByRole("button", { name: "Create account" }),
    ).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Name for 1000")).not.toBeInTheDocument();
    await user.click(within(nav).getByRole("button", { name: "journals" }));
    expect(
      screen.queryByRole("heading", { name: "Balanced journal" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Validate" }),
    ).not.toBeInTheDocument();
    await user.click(within(nav).getByRole("button", { name: "inquiry" }));
    expect(
      screen.queryByRole("button", { name: "Reverse" }),
    ).not.toBeInTheDocument();
    await user.click(within(nav).getByRole("button", { name: "fiscal" }));
    expect(
      screen.queryByRole("heading", { name: "New fiscal year" }),
    ).not.toBeInTheDocument();
  });

  it("announces workspace loading and integrity exception states", async () => {
    const base = vi.mocked(fetch).getMockImplementation()!;
    let integrityRuns = 0;
    vi.mocked(fetch).mockImplementation(
      (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        if (url.endsWith("/ledger/integrity")) {
          integrityRuns += 1;
          return integrityRuns === 1
            ? json({ ok: false })
            : json({ detail: "Integrity service unavailable" }, 503);
        }
        return base(input, init);
      },
    );
    const user = await signIn();
    await user.click(screen.getByRole("button", { name: "Run integrity" }));
    expect(await screen.findByRole("status")).toHaveTextContent(
      "exceptions require review",
    );
    await user.click(screen.getByRole("button", { name: "Run integrity" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Integrity service unavailable",
    );
  });

  it("validates journal account selection and reports workflow and partial bulk failures", async () => {
    const base = vi.mocked(fetch).getMockImplementation()!;
    vi.mocked(fetch).mockImplementation(
      (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        if (url.endsWith("/journals/bulk"))
          return json({ succeeded: [], failed: [{ detail: "Closed period" }] });
        if (/\/journals\/b[123]\/(validate|approve|post)$/.test(url))
          return json({ detail: "Workflow denied" }, 409);
        return base(input, init);
      },
    );
    const user = await signIn();
    await user.click(screen.getByRole("button", { name: "journals" }));
    await user.selectOptions(screen.getByLabelText("Credit account"), "a1");
    await user.click(
      screen.getByRole("button", { name: "Create draft batch" }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "two different accounts",
    );
    await user.click(screen.getByRole("button", { name: "Validate" }));
    expect(
      (await screen.findByText("Workflow denied")).closest('[role="alert"]'),
    ).toBeInTheDocument();
    await user.click(screen.getByLabelText("Mark B-DRAFT"));
    await user.click(screen.getByRole("button", { name: "Bulk validate" }));
    expect(
      (await screen.findByText("0 succeeded; 1 failed: Closed period")).closest(
        '[role="status"]',
      ),
    ).toBeInTheDocument();
  });

  it("blocks reversal without an open period and reports report execution failures", async () => {
    const base = vi.mocked(fetch).getMockImplementation()!;
    vi.mocked(fetch).mockImplementation(
      (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        if (url.endsWith("/fiscal/periods"))
          return json(
            periods.map((period) => ({ ...period, status: "closed" })),
          );
        if (url.endsWith("/reports/run"))
          return json({ detail: "Report parameters rejected" }, 422);
        if (url.endsWith("/reports/runs/run1/reproduce"))
          return json({ detail: "Saved run missing" }, 404);
        return base(input, init);
      },
    );
    const user = await signIn();
    await user.click(screen.getByRole("button", { name: "inquiry" }));
    await user.click(screen.getByRole("button", { name: "Reverse" }));
    await user.click(
      screen.getByRole("button", { name: "Post linked reversal" }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "No open fiscal period",
    );
    await user.click(screen.getByRole("button", { name: "reports" }));
    await user.selectOptions(
      screen.getByLabelText("Report"),
      "chart_of_accounts",
    );
    await user.click(screen.getByRole("button", { name: "Run report" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Report parameters rejected",
    );
    await user.click(screen.getByRole("button", { name: /trial balance/ }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Saved run missing",
    );
  });

  it("previews and applies controlled imports and exercises administrator forms", async () => {
    const user = await signIn();
    await user.click(screen.getByRole("button", { name: "admin" }));
    await screen.findByRole("heading", { name: "Users and roles" });
    const csvInputs = [
      screen.getByLabelText("Account CSV"),
      screen.getByLabelText("Journal CSV"),
    ];
    fireEvent.change(csvInputs[0], {
      target: {
        files: [new File(["code,name"], "accounts.csv", { type: "text/csv" })],
      },
    });
    const accountCard = csvInputs[0].closest("article")!;
    await user.click(
      within(accountCard).getByRole("button", { name: "Preview" }),
    );
    await waitFor(() =>
      expect(
        within(accountCard).getAllByText("2", { selector: "dd" }),
      ).toHaveLength(2),
    );
    await user.click(
      within(accountCard).getByRole("button", { name: "Apply validated file" }),
    );
    expect(await within(accountCard).findByRole("status")).toHaveTextContent(
      "2 accounts created; 0 updated",
    );

    await user.click(screen.getByRole("button", { name: "Create role" }));
    expect(
      (await screen.findByText(/least-privilege reporting access/)).closest(
        '[role="status"]',
      ),
    ).toBeInTheDocument();
    await user.type(screen.getByLabelText("Email"), "new@example.com");
    await user.type(screen.getByLabelText("Display name"), "New User");
    await user.type(
      screen.getByLabelText("Temporary password"),
      "LongPassword123!",
    );
    await user.click(screen.getByRole("button", { name: "Add user" }));
    expect(
      (await screen.findByText(/membership created/)).closest(
        '[role="status"]',
      ),
    ).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText("Density"), "compact");
    await user.click(screen.getByRole("button", { name: "Save ledger view" }));
    expect(
      (await screen.findByText(/Saved view created/)).closest(
        '[role="status"]',
      ),
    ).toBeInTheDocument();
  });

  it("handles unbalanced close previews, budget errors, and downloadable report formats", async () => {
    const base = vi.mocked(fetch).getMockImplementation()!;
    vi.mocked(fetch).mockImplementation(
      (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        if (url.endsWith("/budgets") && init?.method === "PUT")
          return json({ detail: "Budget period locked" }, 409);
        if (url.includes("close-preview"))
          return json({
            balanced: false,
            profit_loss: "1.00",
            closing_lines: 1,
            opening_lines: 0,
          });
        if (url.endsWith("/reports/run") && init?.method === "POST")
          return Promise.resolve(new Response("pdf", { status: 200 }));
        return base(input, init);
      },
    );
    class TestURL extends URL {
      static createObjectURL = vi.fn(() => "blob:report");
      static revokeObjectURL = vi.fn();
    }
    vi.stubGlobal("URL", TestURL);
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(
      () => undefined,
    );
    const user = await signIn();
    await user.click(screen.getByRole("button", { name: "planning" }));
    await user.click(
      screen.getByRole("button", { name: "Save budget version" }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Budget period locked",
    );
    await user.click(screen.getByRole("button", { name: "Preview close" }));
    expect(await screen.findByText("Exception")).toBeVisible();
    expect(
      screen.getByRole("button", { name: "Execute non-destructive close" }),
    ).toBeDisabled();

    await user.click(screen.getByRole("button", { name: "reports" }));
    await user.selectOptions(screen.getByLabelText("Report"), "general_ledger");
    expect(screen.getByLabelText("Fiscal period")).toBeVisible();
    await user.selectOptions(screen.getByLabelText("Output"), "pdf");
    await user.click(screen.getByRole("button", { name: "Run report" }));
    expect(await screen.findByRole("status")).toHaveTextContent(
      "PDF export generated",
    );
    await user.selectOptions(screen.getByLabelText("Report"), "integrity");
    expect(screen.queryByLabelText("Fiscal period")).not.toBeInTheDocument();
  });

  it("shows import validation exceptions, journal entry counts, and upload failures", async () => {
    const base = vi.mocked(fetch).getMockImplementation()!;
    let previews = 0;
    vi.mocked(fetch).mockImplementation(
      (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        if (url.includes("/imports/") && url.endsWith("/preview")) {
          previews += 1;
          if (previews === 1)
            return json({
              rows: 2,
              valid: 1,
              errors: [{ row: 2, message: "Unknown account" }],
            });
          if (previews === 2) return json({ rows: 2, entries: 2, errors: [] });
          return json({ detail: "Upload interrupted" }, 503);
        }
        return base(input, init);
      },
    );
    const user = await signIn();
    await user.click(screen.getByRole("button", { name: "admin" }));
    await screen.findByRole("heading", { name: "Account import" });
    const accountInput = screen.getByLabelText("Account CSV");
    const accountCard = accountInput.closest("article")!;
    fireEvent.change(accountInput, {
      target: { files: [new File(["bad"], "bad.csv")] },
    });
    await user.click(
      within(accountCard).getByRole("button", { name: "Preview" }),
    );
    expect(
      await within(accountCard).findByText("Row 2: Unknown account"),
    ).toBeVisible();
    expect(
      within(accountCard).getByRole("button", { name: "Apply validated file" }),
    ).toBeDisabled();

    const journalInput = screen.getByLabelText("Journal CSV");
    const journalCard = journalInput.closest("article")!;
    fireEvent.change(journalInput, {
      target: { files: [new File(["ok"], "journals.csv")] },
    });
    await user.click(
      within(journalCard).getByRole("button", { name: "Preview" }),
    );
    expect(await within(journalCard).findByRole("status")).toHaveTextContent(
      "ready to apply",
    );
    fireEvent.change(journalInput, {
      target: { files: [new File(["retry"], "retry.csv")] },
    });
    await user.click(
      within(journalCard).getByRole("button", { name: "Preview" }),
    );
    expect(await within(journalCard).findByRole("status")).toHaveTextContent(
      "Upload interrupted",
    );
  });
});
