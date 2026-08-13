import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import {
  AmountCell,
  Badge,
  Banner,
  Button,
  Card,
  Checkbox,
  CompanySwitcher,
  DataTable,
  Dialog,
  DigestValue,
  EmptyState,
  Field,
  IconButton,
  Input,
  KeyValueList,
  PageHeader,
  ProgressBar,
  Select,
  SidebarNav,
  SortHeader,
  StatusPill,
  Switch,
  Tabs,
  Textarea,
} from ".";

describe("ledger design-system primitives", () => {
  it("preserves fixed-decimal strings and accounting-negative notation", () => {
    render(
      <>
        <AmountCell value="-1234.5000" currency="SGD" side="credit" />
        <AmountCell value="0.00" side="debit" />
      </>,
    );

    expect(screen.getByText("(1234.5000)")).toBeVisible();
    expect(screen.getByText("SGD")).toBeVisible();
    expect(
      screen.getByText("(1234.5000)").closest("[data-side]"),
    ).toHaveAttribute("data-side", "credit");
    expect(screen.getByText("—")).toBeVisible();
  });

  it("owns lifecycle labels and accessible field errors", () => {
    render(
      <>
        <StatusPill status="approved" />
        <Field
          label="Posting date"
          htmlFor="posting-date"
          error="Closed period"
        >
          <Input />
        </Field>
      </>,
    );

    expect(screen.getByText("Approved")).toHaveClass("ds-status--approved");
    expect(screen.getByLabelText("Posting date")).toHaveAttribute(
      "aria-describedby",
      "posting-date-error",
    );
    expect(screen.getByLabelText("Posting date")).toHaveAttribute(
      "aria-invalid",
      "true",
    );
  });

  it("gates destructive confirmation, traps focus, closes on Escape, and returns focus", async () => {
    const user = userEvent.setup();
    const confirm = vi.fn();
    function Harness() {
      const [open, setOpen] = useState(false);
      return (
        <>
          <button type="button" onClick={() => setOpen(true)}>
            Open cutover
          </button>
          <Dialog
            open={open}
            title="Apply cutover"
            confirmWord="APPLY"
            confirmLabel="Apply"
            onConfirm={confirm}
            onCancel={() => setOpen(false)}
          />
        </>
      );
    }
    render(<Harness />);
    const trigger = screen.getByRole("button", { name: "Open cutover" });
    await user.click(trigger);
    const dialog = screen.getByRole("dialog", { name: "Apply cutover" });
    const apply = within(dialog).getByRole("button", { name: "Apply" });
    expect(apply).toBeDisabled();
    await user.type(
      within(dialog).getByLabelText("Type APPLY to continue"),
      "APPLY",
    );
    expect(apply).toBeEnabled();
    apply.focus();
    await user.tab();
    expect(
      within(dialog).getByLabelText("Type APPLY to continue"),
    ).toHaveFocus();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
    expect(confirm).not.toHaveBeenCalled();
  });

  it("keeps navigation badges decorative and tabs keyboard operable", async () => {
    const user = userEvent.setup();
    const navigate = vi.fn();
    const change = vi.fn();
    render(
      <>
        <SidebarNav
          groups={[
            {
              label: "Books",
              items: [
                {
                  id: "journals",
                  label: "Journals",
                  icon: "list-checks",
                  badge: 3,
                  readOnly: true,
                },
              ],
            },
          ]}
          onNavigate={navigate}
        />
        <Tabs
          tabs={[
            { id: "one", label: "One" },
            { id: "two", label: "Two" },
          ]}
          activeId="one"
          onChange={change}
        />
      </>,
    );
    await user.click(screen.getByRole("button", { name: "Journals" }));
    expect(navigate).toHaveBeenCalledWith("journals");
    screen.getByRole("tab", { name: "One" }).focus();
    await user.keyboard("{ArrowRight}");
    expect(change).toHaveBeenCalledWith("two");
  });

  it("renders core variants, actions, and loading semantics", async () => {
    const user = userEvent.setup();
    const click = vi.fn();
    render(
      <>
        <Button variant="danger" size="lg" icon="x" iconAfter="check" fullWidth>
          Remove
        </Button>
        <Button busy>Saving</Button>
        <IconButton icon="settings" label="Settings" selected onClick={click} />
        <Card
          title="Control card"
          description="Supporting context"
          actions={<Button size="sm">Act</Button>}
          footer="Audit footer"
          padded={false}
        >
          Body
        </Card>
        <Badge tone="warning" mono>
          Review
        </Badge>
      </>,
    );
    expect(screen.getByRole("button", { name: "Saving" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Saving" })).toHaveAttribute(
      "aria-busy",
      "true",
    );
    await user.click(screen.getByRole("button", { name: "Settings" }));
    expect(click).toHaveBeenCalledOnce();
    expect(screen.getByRole("button", { name: "Settings" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByText("Audit footer")).toBeVisible();
    expect(screen.getByText("Review")).toHaveClass("ds-badge--warning");
  });

  it("renders tables, sorting, totals, empty states, and keyboard row activation", async () => {
    const user = userEvent.setup();
    const rowClick = vi.fn();
    const sort = vi.fn();
    const { rerender } = render(
      <DataTable
        caption="Ledger rows"
        captionVisible
        columns={[
          { key: "label", header: "Label", wrap: true },
          { key: "amount", header: "Amount", numeric: true, mono: true },
        ]}
        rows={[{ id: "r1", label: "Cash", amount: "10.00" }]}
        rowKey={(row) => String(row.id)}
        footRow={{ label: "Total", amount: "10.00" }}
        onRowClick={rowClick}
        stickyHeader={false}
      />,
    );
    expect(screen.getByText("Ledger rows")).toBeVisible();
    await user.click(screen.getByText("Cash"));
    expect(rowClick).toHaveBeenCalledOnce();
    screen.getByText("Cash").closest("tr")?.focus();
    await user.keyboard(" ");
    expect(rowClick).toHaveBeenCalledTimes(2);
    rerender(
      <>
        <DataTable
          caption="Empty ledger"
          columns={[{ key: "label", header: "Label" }]}
          rows={[]}
          empty="Nothing posted"
        />
        <SortHeader label="Amount" direction="desc" onClick={sort} />
      </>,
    );
    expect(screen.getByText("Nothing posted")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Amount" }));
    expect(sort).toHaveBeenCalledOnce();
  });

  it("handles amount, digest, and key-value display variants", async () => {
    const user = userEvent.setup();
    const clipboard = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText: clipboard },
    });
    render(
      <>
        <AmountCell value={1234.5} emphasis />
        <AmountCell value={null} zeroAs="Nil" />
        <DigestValue value="abcdefghijklmnopqrstuvwxyz0123456789" truncate />
        <KeyValueList
          columns={2}
          items={[
            { label: "Rows", value: 2, numeric: true },
            { label: "Digest", value: "abc", mono: true },
          ]}
        />
      </>,
    );
    expect(screen.getByText("1,234.50")).toBeVisible();
    expect(screen.getByText("Nil")).toBeVisible();
    expect(screen.getByText(/abcdefghijkl…/)).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Copy digest" }));
    expect(clipboard).toHaveBeenCalledWith(
      "abcdefghijklmnopqrstuvwxyz0123456789",
    );
    expect(screen.getByText("Copied")).toBeVisible();
    expect(screen.getByText("2")).toHaveAttribute("data-numeric", "");
  });

  it("supports form option, textarea, checkbox, switch, and immutable field states", async () => {
    const user = userEvent.setup();
    const change = vi.fn();
    render(
      <>
        <Field
          label="Account"
          htmlFor="account"
          hint="Postable accounts only"
          required
          immutable
        >
          <Select
            placeholder="Choose"
            options={[
              "Cash",
              { value: "revenue", label: "Revenue", disabled: true },
            ]}
          />
        </Field>
        <Textarea aria-label="Memo" mono invalid />
        <Checkbox
          label="Selected"
          description="Included in bulk"
          indeterminate
        />
        <Checkbox label="Checked" checked readOnly />
        <Switch label="Compact" onChange={change} />
      </>,
    );
    expect(screen.getByText("Postable accounts only")).toBeVisible();
    expect(screen.getByRole("option", { name: "Revenue" })).toBeDisabled();
    expect(screen.getByLabelText("Memo")).toHaveAttribute(
      "aria-invalid",
      "true",
    );
    expect(
      screen.getByRole("checkbox", { name: "Selected Included in bulk" }),
    ).toHaveProperty("indeterminate", true);
    await user.click(screen.getByRole("checkbox", { name: "Compact" }));
    expect(change).toHaveBeenCalledOnce();
  });

  it("announces banner and progress variants and supports dismissal", async () => {
    const user = userEvent.setup();
    const dismiss = vi.fn();
    render(
      <>
        <Banner
          tone="danger"
          title="Failed"
          correlationId="corr-1"
          onDismiss={dismiss}
        >
          Retry later
        </Banner>
        <Banner tone="info" live="off">
          Static note
        </Banner>
        <ProgressBar label="Import" value={140} status="succeeded" />
        <ProgressBar label="Queue" indeterminate status="queued" />
        <EmptyState
          icon="search-x"
          kind="no-match"
          title="No matches"
          description="Change filters"
          action={<Button>Clear</Button>}
        />
      </>,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Reference corr-1");
    expect(screen.getByRole("note")).toHaveTextContent("Static note");
    expect(screen.getByRole("progressbar", { name: "Import" })).toHaveAttribute(
      "aria-valuenow",
      "100",
    );
    expect(
      screen.getByRole("progressbar", { name: "Queue" }),
    ).not.toHaveAttribute("aria-valuenow");
    await user.click(screen.getByRole("button", { name: "Dismiss" }));
    expect(dismiss).toHaveBeenCalledOnce();
    expect(screen.getByRole("heading", { name: "No matches" })).toBeVisible();
  });

  it("switches companies and renders page data-state variants", async () => {
    const user = userEvent.setup();
    const select = vi.fn();
    const memberships = [
      { id: "c1", company: "Acme", code: "AC", role: "Approver" },
      { id: "c2", company: "Beta", code: "BT", role: "Viewer" },
    ];
    render(
      <>
        <CompanySwitcher
          company="Acme"
          code="AC"
          role="Approver"
          memberships={memberships}
          onSelect={select}
          inverse={false}
        />
        <PageHeader
          eyebrow="Acme"
          title="Journals"
          meta="FY2026"
          actions={<Button>Refresh</Button>}
          dataState="failed"
          updatedAt="10:30"
        />
      </>,
    );
    fireEvent.change(screen.getByLabelText("Company"), {
      target: { value: "c2" },
    });
    expect(select).toHaveBeenCalledWith(memberships[1]);
    await user.click(
      screen.getByRole("button", { name: /Acme AC · Approver/ }),
    );
    expect(
      screen.getByRole("listbox", { name: "Active company" }),
    ).toBeVisible();
    await user.click(
      within(screen.getByRole("listbox", { name: "Active company" })).getByRole(
        "option",
        { name: /Beta/ },
      ),
    );
    expect(select).toHaveBeenLastCalledWith(memberships[1]);
    expect(screen.getByText(/Load failed · 10:30/)).toBeVisible();
  });
});
