import React from "react";
import { Icon } from "../core/Icon.jsx";

export function SidebarNav({ groups = [], activeId, onNavigate, footer, style, ...rest }) {
  return (
    <nav
      aria-label="Workspaces"
      style={{
        width: "var(--layout-sidebar-w)",
        flex: "0 0 auto",
        background: "var(--surface-nav)",
        borderRight: "1px solid var(--border-hairline)",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        padding: "var(--space-6) var(--space-4)",
        gap: "var(--space-6)",
        overflowY: "auto",
        ...style,
      }}
      {...rest}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-7)" }}>
        {groups.map((g) => (
          <div key={g.label} style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
            <p style={{ font: "var(--type-overline)", letterSpacing: "var(--tracking-caps)", textTransform: "uppercase", color: "var(--text-muted)", padding: "0 var(--space-4) var(--space-2)" }}>
              {g.label}
            </p>
            {g.items.map((it) => {
              const active = it.id === activeId;
              return (
                <a
                  key={it.id}
                  href={`#${it.id}`}
                  aria-current={active ? "page" : undefined}
                  onClick={(e) => { e.preventDefault(); onNavigate && onNavigate(it.id); }}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "var(--space-4)",
                    padding: "0 var(--space-4)",
                    height: 30,
                    borderRadius: "var(--radius-sm)",
                    textDecoration: "none",
                    font: active ? "var(--type-label)" : "var(--type-body-sm)",
                    color: active ? "var(--text-accent)" : "var(--text-secondary)",
                    background: active ? "var(--surface-selected)" : "transparent",
                    transition: "var(--transition-control)",
                  }}
                >
                  <Icon name={it.icon} size={15} />
                  <span style={{ flex: 1, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{it.label}</span>
                  {it.badge != null && (
                    <span data-numeric="" style={{ font: "var(--type-mono)", fontSize: "var(--text-2xs)", color: "var(--text-muted)" }}>{it.badge}</span>
                  )}
                  {it.readOnly && <Icon name="eye" size={12} style={{ color: "var(--text-muted)" }} />}
                </a>
              );
            })}
          </div>
        ))}
      </div>
      {footer && <div style={{ padding: "0 var(--space-4)" }}>{footer}</div>}
    </nav>
  );
}
