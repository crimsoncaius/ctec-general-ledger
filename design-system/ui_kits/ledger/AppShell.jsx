import React from "react";
import { SidebarNav } from "../../components/navigation/SidebarNav.jsx";
import { CompanySwitcher } from "../../components/navigation/CompanySwitcher.jsx";
import { IconButton } from "../../components/core/IconButton.jsx";
import { Icon } from "../../components/core/Icon.jsx";

const ALL_NAV = [
  { label: "Books", items: [
    { id: "overview", label: "Overview", icon: "layout-dashboard", cap: "journals.view" },
    { id: "accounts", label: "Chart of accounts", icon: "list-tree", cap: "accounts.view" },
    { id: "fiscal", label: "Fiscal calendar", icon: "calendar-range", cap: "fiscal.view" },
  ]},
  { label: "Ledger", items: [
    { id: "journals", label: "Journals", icon: "file-stack", cap: "journals.view", badge: 6 },
    { id: "inquiry", label: "Posted inquiry", icon: "search", cap: "journals.inquire" },
  ]},
  { label: "Close & planning", items: [
    { id: "close", label: "Budgets & close", icon: "scale", cap: "fiscal.close" },
  ]},
  { label: "Output", items: [
    { id: "reports", label: "Reports", icon: "file-text", cap: "reports.run" },
    { id: "designer", label: "Report designer", icon: "table-properties", cap: "reports.custom.design" },
  ]},
  { label: "Company", items: [
    { id: "admin", label: "Administration", icon: "settings", cap: "company.manage" },
    { id: "migration", label: "Legacy migration", icon: "database-zap", cap: "migration.run" },
  ]},
];

export function AppShell({ user, company, code, role, capabilities = [], memberships = [], activeId, onNavigate, onSwitch, density = "comfortable", onDensity, children }) {
  const groups = ALL_NAV
    .map((g) => ({ label: g.label, items: g.items.filter((i) => capabilities.includes(i.cap)).map((i) => ({ ...i, readOnly: readOnlyFor(i.id, capabilities) })) }))
    .filter((g) => g.items.length);

  return (
    <div data-density={density} style={{ minHeight: "100vh", display: "flex", flexDirection: "column", background: "var(--surface-page)" }}>
      <header
        style={{
          height: "var(--layout-header-h)",
          flex: "0 0 auto",
          background: "var(--surface-header)",
          display: "flex",
          alignItems: "center",
          gap: "var(--space-6)",
          padding: "0 var(--space-6)",
        }}
      >
        <span style={{ font: "var(--weight-semibold) var(--text-lg)/1 var(--font-sans)", letterSpacing: "0.04em", color: "var(--text-inverse)", whiteSpace: "nowrap" }}>
          CTec <span style={{ color: "var(--blue-300)" }}>Ledger</span>
        </span>
        <CompanySwitcher company={company} code={code} role={role} memberships={memberships} onSelect={onSwitch} />
        <div style={{ flex: 1 }} />
        <button
          type="button"
          onClick={() => onDensity && onDensity(density === "comfortable" ? "compact" : "comfortable")}
          style={{ display: "inline-flex", alignItems: "center", gap: "var(--space-3)", height: 28, padding: "0 var(--space-4)", background: "transparent", border: "1px solid rgba(255,255,255,0.18)", borderRadius: "var(--radius-sm)", color: "var(--text-inverse)", font: "var(--type-caption)", cursor: "pointer" }}
        >
          <Icon name={density === "compact" ? "rows-3" : "rows-2"} size={13} />
          {density === "compact" ? "Compact" : "Comfortable"}
        </button>
        <span style={{ display: "flex", alignItems: "center", gap: "var(--space-4)", color: "var(--text-inverse)", font: "var(--type-caption)" }}>
          <span style={{ opacity: 0.85 }}>{user}</span>
          <IconButton icon="log-out" label="Sign out" style={{ color: "var(--text-inverse)" }} />
        </span>
      </header>
      <div style={{ display: "flex", flex: 1, minHeight: 0 }}>
        <SidebarNav
          groups={groups}
          activeId={activeId}
          onNavigate={onNavigate}
          footer={<p style={{ font: "var(--type-caption)", color: "var(--text-muted)" }}>Signed in as <strong style={{ font: "var(--type-label)" }}>{role}</strong>. Destinations follow your capabilities.</p>}
        />
        <main style={{ flex: 1, minWidth: 0, overflow: "auto" }}>
          <div style={{ maxWidth: "var(--layout-content-max)", padding: "0 var(--layout-gutter) var(--space-11)" }}>{children}</div>
        </main>
      </div>
    </div>
  );
}

function readOnlyFor(id, caps) {
  if (id === "accounts") return !caps.includes("accounts.update");
  if (id === "journals") return !caps.includes("journals.create") && !caps.includes("journals.post");
  return false;
}
