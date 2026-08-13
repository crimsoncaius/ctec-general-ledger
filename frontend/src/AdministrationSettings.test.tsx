import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AdministrationSettings } from "./AdministrationSettings";

const company = { id: "c1", code: "ACME", name: "Acme", base_currency_code: "SGD", role: "Administrator", capabilities: [] };
const settings = { name: "Acme", timezone: "Asia/Singapore", rounding_places: 2, use_bankers_rounding: true };
const roles = [{ id: "r1", name: "Approver", description: "Approves", system: true, active: true }];
const permissions = [
  { id: "p1", code: "journals.approve", description: "Approve journals" },
  { id: "p2", code: "reports.run", description: "Run reports" },
];

function response(body: unknown, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } }));
}

describe("AdministrationSettings", () => {
  beforeEach(() => vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.endsWith("/administration/company")) return response(init?.method === "PUT" ? { ...settings, name: "Acme Updated" } : settings);
    if (url.endsWith("/administration/roles")) return response(roles);
    if (url.endsWith("/administration/permissions")) return response(permissions);
    if (url.endsWith("/administration/roles/r1/permissions")) return response(init?.method === "PUT" ? {} : { permissions: ["journals.approve"] });
    return response({}, 404);
  })));

  it("renders nothing for users without management capabilities", () => {
    const { container } = render(<AdministrationSettings token="t" company={company} capabilities={new Set()} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("loads and saves company presentation controls", async () => {
    const user = userEvent.setup();
    render(<AdministrationSettings token="t" company={company} capabilities={new Set(["company.manage"])} />);
    expect(await screen.findByLabelText("Company name")).toHaveValue("Acme");
    await user.clear(screen.getByLabelText("Company name"));
    await user.type(screen.getByLabelText("Company name"), "Acme Updated");
    await user.clear(screen.getByLabelText("Rounding places"));
    await user.type(screen.getByLabelText("Rounding places"), "4");
    await user.click(screen.getByRole("checkbox", { name: "Bankers rounding" }));
    await user.click(screen.getByRole("button", { name: "Save company settings" }));
    expect(await screen.findByRole("status")).toHaveTextContent("saved with audit evidence");
    const request = vi.mocked(fetch).mock.calls.find(([url, init]) => String(url).endsWith("/administration/company") && init?.method === "PUT")?.[1];
    expect(JSON.parse(String(request?.body))).toMatchObject({ name: "Acme Updated", rounding_places: 4, use_bankers_rounding: false });
  });

  it("loads, toggles, and atomically saves role capabilities", async () => {
    const user = userEvent.setup();
    render(<AdministrationSettings token="t" company={company} capabilities={new Set(["users.manage"])} />);
    await waitFor(() => expect(screen.getByRole("option", { name: /Approver/ })).toBeInTheDocument());
    await user.selectOptions(screen.getByLabelText("Role to configure"), "r1");
    expect(await screen.findByRole("checkbox", { name: /journals.approve/ })).toBeChecked();
    await user.click(screen.getByRole("checkbox", { name: /reports.run/ }));
    await user.click(screen.getByRole("button", { name: "Save role capabilities" }));
    expect(await screen.findByRole("status")).toHaveTextContent("replaced atomically");
    const request = vi.mocked(fetch).mock.calls.find(([url, init]) => String(url).endsWith("/roles/r1/permissions") && init?.method === "PUT")?.[1];
    expect(JSON.parse(String(request?.body))).toEqual({ permissions: ["journals.approve", "reports.run"] });
    await user.selectOptions(screen.getByLabelText("Role to configure"), "");
    expect(screen.queryByRole("button", { name: "Save role capabilities" })).not.toBeInTheDocument();
  });

  it("announces load and save failures as status messages", async () => {
    vi.mocked(fetch).mockImplementation(() => response({ detail: "Settings unavailable" }, 503));
    render(<AdministrationSettings token="t" company={company} capabilities={new Set(["company.manage"])} />);
    expect(await screen.findByRole("status")).toHaveTextContent("Settings unavailable");
  });

  it("announces company and role save failures and preserves editable controls", async () => {
    vi.mocked(fetch).mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/administration/company") && init?.method === "PUT") return response({ detail: "Invalid timezone" }, 422);
      if (url.endsWith("/administration/company")) return response(settings);
      if (url.endsWith("/administration/roles")) return response(roles);
      if (url.endsWith("/administration/permissions")) return response(permissions);
      if (url.endsWith("/roles/r1/permissions") && init?.method === "PUT") return response({ detail: "System role locked" }, 409);
      if (url.endsWith("/roles/r1/permissions")) return response({ permissions: [] });
      return response({});
    });
    const user = userEvent.setup();
    render(<AdministrationSettings token="t" company={company} capabilities={new Set(["company.manage", "users.manage"])} />);
    await screen.findByLabelText("Company name");
    await user.click(screen.getByRole("button", { name: "Save company settings" }));
    expect(await screen.findByRole("status")).toHaveTextContent("Invalid timezone");
    expect(screen.getByRole("button", { name: "Save company settings" })).toBeEnabled();
    await user.selectOptions(screen.getByLabelText("Role to configure"), "r1");
    await screen.findByRole("button", { name: "Save role capabilities" });
    await user.click(screen.getByRole("button", { name: "Save role capabilities" }));
    expect(await screen.findByRole("status")).toHaveTextContent("System role locked");
  });
});
