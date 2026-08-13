import React from "react";
import { Icon } from "../core/Icon.jsx";

export function Tabs({ tabs = [], activeId, onChange, style, ...rest }) {
  return (
    <div
      role="tablist"
      aria-label="Sections"
      style={{ display: "flex", gap: "var(--space-6)", borderBottom: "1px solid var(--border-hairline)", ...style }}
      {...rest}
    >
      {tabs.map((t) => {
        const active = t.id === activeId;
        return (
          <button
            key={t.id}
            role="tab"
            aria-selected={active}
            tabIndex={active ? 0 : -1}
            onClick={() => onChange && onChange(t.id)}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "var(--space-3)",
              padding: "var(--space-4) 0",
              marginBottom: -1,
              background: "none",
              border: "none",
              borderBottom: `2px solid ${active ? "var(--blue-500)" : "transparent"}`,
              color: active ? "var(--text-primary)" : "var(--text-secondary)",
              font: active ? "var(--type-label)" : "var(--type-body-sm)",
              cursor: "pointer",
              transition: "var(--transition-control)",
            }}
          >
            {t.icon && <Icon name={t.icon} size={14} />}
            {t.label}
            {t.count != null && (
              <span data-numeric="" style={{ font: "var(--type-mono)", fontSize: "var(--text-xs)", color: "var(--text-muted)" }}>{t.count}</span>
            )}
          </button>
        );
      })}
    </div>
  );
}
