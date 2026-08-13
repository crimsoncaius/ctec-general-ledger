import React from "react";
import { Icon } from "../core/Icon.jsx";

export function CompanySwitcher({ company, code, role, memberships = [], onSelect, inverse = true, style, ...rest }) {
  const [open, setOpen] = React.useState(false);
  const fg = inverse ? "var(--text-inverse)" : "var(--text-primary)";
  return (
    <div style={{ position: "relative", ...style }} {...rest}>
      <button
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        style={{
          display: "flex",
          alignItems: "center",
          gap: "var(--space-4)",
          height: 34,
          padding: "0 var(--space-4)",
          background: open ? (inverse ? "rgba(255,255,255,0.12)" : "var(--surface-hover)") : "transparent",
          border: `1px solid ${inverse ? "rgba(255,255,255,0.18)" : "var(--border-hairline)"}`,
          borderRadius: "var(--radius-sm)",
          color: fg,
          cursor: "pointer",
          transition: "var(--transition-control)",
        }}
      >
        <span
          aria-hidden="true"
          style={{ display: "grid", placeItems: "center", width: 22, height: 22, borderRadius: "var(--radius-xs)", background: "var(--blue-500)", color: "var(--n-0)", font: "var(--type-mono)", fontSize: "var(--text-2xs)", fontWeight: "var(--weight-semibold)" }}
        >
          {code.slice(0, 2)}
        </span>
        <span style={{ display: "flex", flexDirection: "column", alignItems: "flex-start", lineHeight: 1.15 }}>
          <span style={{ font: "var(--type-label)" }}>{company}</span>
          <span style={{ font: "var(--type-mono)", fontSize: "var(--text-2xs)", opacity: 0.7 }}>{code}{role ? ` · ${role}` : ""}</span>
        </span>
        <Icon name="chevrons-up-down" size={13} style={{ opacity: 0.65 }} />
      </button>
      {open && (
        <div
          role="listbox"
          aria-label="Active company"
          style={{
            position: "absolute",
            top: "calc(100% + 6px)",
            left: 0,
            minWidth: 280,
            background: "var(--surface-raised)",
            borderRadius: "var(--radius-md)",
            boxShadow: "var(--shadow-menu)",
            padding: "var(--space-3)",
            zIndex: 40,
          }}
        >
          <p style={{ font: "var(--type-overline)", letterSpacing: "var(--tracking-caps)", textTransform: "uppercase", color: "var(--text-muted)", padding: "var(--space-3) var(--space-4)" }}>
            Switching company reloads all company data
          </p>
          {memberships.map((m) => {
            const active = m.code === code;
            return (
              <button
                key={m.code}
                type="button"
                role="option"
                aria-selected={active}
                onClick={() => { setOpen(false); onSelect && onSelect(m); }}
                style={{
                  display: "flex",
                  width: "100%",
                  alignItems: "center",
                  justifyContent: "space-between",
                  gap: "var(--space-5)",
                  padding: "var(--space-4)",
                  background: active ? "var(--surface-selected)" : "transparent",
                  border: "none",
                  borderRadius: "var(--radius-sm)",
                  cursor: "pointer",
                  textAlign: "left",
                  font: "var(--type-body-sm)",
                  color: "var(--text-body)",
                }}
              >
                <span style={{ display: "flex", flexDirection: "column" }}>
                  <span style={{ font: "var(--type-label)" }}>{m.company}</span>
                  <span style={{ font: "var(--type-mono)", fontSize: "var(--text-xs)", color: "var(--text-muted)" }}>{m.code} · {m.role}</span>
                </span>
                {active && <Icon name="check" size={14} style={{ color: "var(--text-accent)" }} />}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
