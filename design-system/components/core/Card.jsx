import React from "react";

export function Card({ title, description, actions, footer, padded = true, children, style, ...rest }) {
  return (
    <section
      style={{
        background: "var(--surface-card)",
        border: "1px solid var(--border-hairline)",
        borderRadius: "var(--radius-md)",
        boxShadow: "var(--shadow-raised)",
        display: "flex",
        flexDirection: "column",
        minWidth: 0,
        ...style,
      }}
      {...rest}
    >
      {(title || actions) && (
        <header
          style={{
            display: "flex",
            alignItems: "flex-start",
            justifyContent: "space-between",
            gap: "var(--space-6)",
            padding: "var(--space-5) var(--card-pad)",
            borderBottom: "1px solid var(--border-hairline)",
          }}
        >
          <div style={{ minWidth: 0 }}>
            {title && <h3 style={{ font: "var(--type-h3)", letterSpacing: "var(--tracking-tight)" }}>{title}</h3>}
            {description && (
              <p style={{ font: "var(--type-caption)", color: "var(--text-muted)", marginTop: "var(--space-2)" }}>{description}</p>
            )}
          </div>
          {actions && <div style={{ display: "flex", gap: "var(--space-3)", flex: "0 0 auto" }}>{actions}</div>}
        </header>
      )}
      <div style={{ padding: padded ? "var(--card-pad)" : 0, minWidth: 0 }}>{children}</div>
      {footer && (
        <footer
          style={{
            padding: "var(--space-5) var(--card-pad)",
            borderTop: "1px solid var(--border-hairline)",
            background: "var(--surface-sunken)",
            font: "var(--type-caption)",
            color: "var(--text-muted)",
            borderRadius: "0 0 var(--radius-md) var(--radius-md)",
          }}
        >
          {footer}
        </footer>
      )}
    </section>
  );
}
