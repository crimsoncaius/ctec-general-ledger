import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AccountManager } from "./AccountManager";
import { FiscalCalendarManager } from "./FiscalCalendarManager";

const company = {
  id: "acme-id",
  code: "ACME",
  name: "Acme Trading Pte Ltd",
  base_currency_code: "SGD",
  role: "Administrator",
  capabilities: [],
};

const accounts = [
  { id: "a1", code: "1000", name: "Cash", account_type: "balance_sheet", currency_code: "SGD", postable: true, active: true },
  { id: "a2", code: "3000", name: "Retained earnings", account_type: "retained_earnings", currency_code: "SGD", postable: true, active: true },
  { id: "a3", code: "T100", name: "Assets", account_type: "title", currency_code: "SGD", postable: false, active: true },
];

function ok(body: unknown = {}) {
  return Promise.resolve(new Response(JSON.stringify(body), { status: 200, headers: { "Content-Type": "application/json" } }));
}

describe("management workflows", () => {
  beforeEach(() => vi.stubGlobal("fetch", vi.fn(() => ok())));

  it("creates a normalized account through the capability-gated form", async () => {
    const user = userEvent.setup();
    const changed = vi.fn().mockResolvedValue(undefined);
    render(<AccountManager accounts={[]} company={company} capabilities={new Set(["accounts.create"])} token="token" onChanged={changed} />);
    await user.type(screen.getByLabelText("Account code"), "7100");
    await user.type(screen.getByLabelText("Account name"), "Testing expense");
    await user.click(screen.getByRole("button", { name: "Create account" }));
    expect(changed).toHaveBeenCalledOnce();
    const request = vi.mocked(fetch).mock.calls[0][1];
    expect(JSON.parse(String(request?.body))).toMatchObject({ code: "7100", currency_code: "SGD", account_type: "balance_sheet" });
  });

  it("normalizes currency, forces title accounts non-postable, and announces failures", async () => {
    vi.mocked(fetch).mockImplementationOnce(() => ok({ detail: "Duplicate account" })).mockImplementationOnce(() => Promise.resolve(new Response(JSON.stringify({ detail: "Duplicate account" }), { status: 409, headers: { "Content-Type": "application/json" } })));
    const user = userEvent.setup();
    render(<AccountManager accounts={[]} company={company} capabilities={new Set(["accounts.create"])} token="token" onChanged={vi.fn()} />);
    await user.type(screen.getByLabelText("Account code"), "T200");
    await user.type(screen.getByLabelText("Account name"), "Liabilities");
    await user.selectOptions(screen.getByLabelText("Type"), "title");
    await user.clear(screen.getByLabelText("Account currency"));
    await user.type(screen.getByLabelText("Account currency"), "usd");
    expect(screen.getByLabelText("Account currency")).toHaveValue("USD");
    expect(screen.getByRole("checkbox", { name: "Postable" })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Create account" }));
    const payload = JSON.parse(String(vi.mocked(fetch).mock.calls[0][1]?.body));
    expect(payload).toMatchObject({ currency_code: "USD", account_type: "title", postable: false });
  });

  it("updates changed accounts, protects constrained toggles, and hides controls without capabilities", async () => {
    const user = userEvent.setup();
    const changed = vi.fn().mockResolvedValue(undefined);
    const { rerender } = render(<AccountManager accounts={accounts} company={company} capabilities={new Set(["accounts.update"])} token="token" onChanged={changed} />);
    expect(screen.queryByRole("button", { name: "Create account" })).not.toBeInTheDocument();
    expect(screen.getByLabelText("Name for 1000").closest("tr")?.querySelector("button")).toBeDisabled();
    expect(screen.getByLabelText("Name for T100").closest("tr")?.querySelector('input[type="checkbox"]')).toBeDisabled();
    const retainedRow = screen.getByLabelText("Name for 3000").closest("tr");
    expect(retainedRow?.querySelectorAll('input[type="checkbox"]')[1]).toBeDisabled();
    await user.clear(screen.getByLabelText("Name for 1000"));
    await user.type(screen.getByLabelText("Name for 1000"), "Main cash");
    await user.click(screen.getByLabelText("Name for 1000").closest("tr")!.querySelector("button")!);
    expect(changed).toHaveBeenCalledOnce();
    expect(await screen.findByRole("status")).toHaveTextContent("Account 1000 updated");

    rerender(<AccountManager accounts={accounts} company={company} capabilities={new Set()} token="token" onChanged={changed} />);
    expect(screen.queryByLabelText("Name for 1000")).not.toBeInTheDocument();
    expect(screen.getByText("Cash")).toBeVisible();
  });

  it("announces an account API error and re-enables the form", async () => {
    vi.mocked(fetch).mockImplementationOnce(() => Promise.resolve(new Response(JSON.stringify({ detail: "Account code exists" }), { status: 409, headers: { "Content-Type": "application/json" } })));
    const user = userEvent.setup();
    render(<AccountManager accounts={[]} company={company} capabilities={new Set(["accounts.create"])} token="token" onChanged={vi.fn()} />);
    await user.type(screen.getByLabelText("Account code"), "1000");
    await user.type(screen.getByLabelText("Account name"), "Duplicate");
    await user.click(screen.getByRole("button", { name: "Create account" }));
    expect(await screen.findByRole("status")).toHaveTextContent("Account code exists");
    expect(screen.getByRole("button", { name: "Create account" })).toBeEnabled();
  });

  it("generates and submits a reviewed 13-period fiscal calendar", async () => {
    const user = userEvent.setup();
    const changed = vi.fn().mockResolvedValue(undefined);
    render(<FiscalCalendarManager token="token" company={company} years={[]} periods={[]} canManage onChanged={changed} />);
    await user.clear(screen.getByLabelText("Year label"));
    await user.type(screen.getByLabelText("Year label"), "FY2030-13");
    await user.clear(screen.getByLabelText("First day"));
    await user.type(screen.getByLabelText("First day"), "2030-01-01");
    await user.clear(screen.getByLabelText("Periods"));
    await user.type(screen.getByLabelText("Periods"), "13");
    await user.click(screen.getByRole("button", { name: "Generate boundaries" }));
    expect(screen.getByLabelText("Label for period 13")).toHaveValue("P13");
    await user.click(screen.getByRole("button", { name: "Save fiscal year" }));
    expect(changed).toHaveBeenCalledOnce();
    const request = vi.mocked(fetch).mock.calls[0][1];
    const payload = JSON.parse(String(request?.body)) as { periods: unknown[] };
    expect(payload.periods).toHaveLength(13);
  });

  it("renders read-only calendar status and validates generation boundaries", async () => {
    render(<FiscalCalendarManager token="token" company={company} years={[]} periods={[{ id: "p1", fiscal_year_id: "fy", period_no: 1, label: "P01", start_date: "2026-01-01", end_date: "2026-01-31", status: "closed" }]} canManage={false} onChanged={vi.fn()} />);
    expect(screen.getByRole("heading", { name: "1 periods" })).toBeVisible();
    expect(screen.getByText("closed")).toBeVisible();
    expect(screen.queryByRole("heading", { name: "New fiscal year" })).not.toBeInTheDocument();
  });

  it("starts after the latest year and announces fiscal save errors", async () => {
    vi.mocked(fetch).mockImplementationOnce(() => Promise.resolve(new Response(JSON.stringify({ detail: "Periods overlap" }), { status: 422, headers: { "Content-Type": "application/json" } })));
    const user = userEvent.setup();
    render(<FiscalCalendarManager token="token" company={company} years={[{ id: "fy", label: "FY2029", start_date: "2029-01-01", end_date: "2029-12-31", closed_at: null }]} periods={[]} canManage onChanged={vi.fn()} />);
    expect(screen.getByLabelText("First day")).toHaveValue("2030-01-01");
    await user.clear(screen.getByLabelText("Periods"));
    await user.type(screen.getByLabelText("Periods"), "0");
    expect(screen.getByRole("button", { name: "Generate boundaries" })).toBeDisabled();
    await user.clear(screen.getByLabelText("Periods"));
    await user.type(screen.getByLabelText("Periods"), "1");
    await user.click(screen.getByRole("button", { name: "Generate boundaries" }));
    await user.clear(screen.getByLabelText("Label for period 1"));
    await user.type(screen.getByLabelText("Label for period 1"), "OPEN");
    await user.click(screen.getByRole("button", { name: "Save fiscal year" }));
    expect(await screen.findByRole("status")).toHaveTextContent("Periods overlap");
    await waitFor(() => expect(screen.getByRole("button", { name: "Save fiscal year" })).toBeEnabled());
  });
});
