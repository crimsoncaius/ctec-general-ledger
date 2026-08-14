import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";

const companies = [
  {
    id: "acme-id",
    code: "ACME",
    name: "Acme Trading Pte Ltd",
    base_currency_code: "SGD",
    role: "Administrator",
    capabilities: ["accounts.view", "journals.view", "journals.create", "journals.validate"],
  },
  {
    id: "north-id",
    code: "NORTH",
    name: "Northstar Services Ltd",
    base_currency_code: "USD",
    role: "Administrator",
    capabilities: ["accounts.view", "journals.view"],
  },
];

function response(body: unknown, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  }));
}

describe("CTec application shell", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const headers = new Headers(init?.headers);
      const company = headers.get("X-Company-ID");
      if (url.endsWith("/auth/token")) return response({ access_token: "test-token" });
      if (url.endsWith("/auth/me")) return response({
        id: "user-id", email: "admin@example.com", display_name: "Demo Administrator", companies,
      });
      if (url.endsWith("/accounts")) return response(company === "north-id" ? [
        { id: "n1", code: "1000", name: "North Cash", account_type: "balance_sheet", currency_code: "USD", postable: true, active: true },
      ] : [
        { id: "a1", code: "1000", name: "Cash at Bank", account_type: "balance_sheet", currency_code: "SGD", postable: true, active: true },
        { id: "a2", code: "4000", name: "Revenue", account_type: "revenue_expense", currency_code: "SGD", postable: true, active: true },
      ]);
      if (url.endsWith("/fiscal/periods")) return response([
        { id: "p1", fiscal_year_id: "fy1", period_no: 1, label: "P01", start_date: "2026-01-01", end_date: "2026-01-28", status: "open" },
      ]);
      if (url.endsWith("/fiscal/years")) return response([
        { id: "fy1", label: "FY2026", start_date: "2026-01-01", end_date: "2026-12-31", closed_at: null },
      ]);
      if (url.endsWith("/journals")) return response([]);
      return response({ detail: "Not mocked" }, 404);
    }));
  });

  it("signs in and changes company-isolated workspace data", async () => {
    const user = userEvent.setup();
    render(<App />);
    expect(screen.getByRole("heading", { name: /financial truth/i })).toBeVisible();
    expect(screen.getByLabelText("Email")).toHaveValue("admin@example.com");
    expect(screen.getByLabelText("Password")).toHaveValue("CTec-Demo-Admin-2026!");
    await user.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByRole("heading", { name: "Acme Trading Pte Ltd" })).toBeVisible();
    expect(await screen.findByText("2", { selector: ".metric-grid strong" })).toBeVisible();

    await user.selectOptions(screen.getByLabelText("Company"), "north-id");
    expect(await screen.findByRole("heading", { name: "Northstar Services Ltd" })).toBeVisible();
    await waitFor(() => {
      expect(screen.getByText("normalized accounts").previousElementSibling).toHaveTextContent("1");
    });
  });

  it("reports authentication errors accessibly", async () => {
    vi.mocked(fetch).mockImplementationOnce(() => response({ detail: "Invalid credentials" }, 401));
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid credentials");
  });
});
