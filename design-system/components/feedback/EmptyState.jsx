import React from "react";
import { Icon } from "../core/Icon.jsx";

export function EmptyState({ icon = "inbox", title, description, action, kind = "no-data", style, ...rest }) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: "var(--space-4)",
        padding: "var(--space-11) var(--space-8)",
        textAlign: "center",
        ...style,
      }}
      data-empty-kind={kind}
      {...rest}
    >
      <Icon name={icon} size={20} style={{ color: "var(--text-muted)" }} />
      <p style={{ font: "var(--type-h3)", color: "var(--text-primary)" }}>{title}</p>
      {description && <p style={{ font: "var(--type-body-sm)", color: "var(--text-muted)", maxWidth: "44ch" }}>{description}</p>}
      {action && <div style={{ marginTop: "var(--space-3)" }}>{action}</div>}
    </div>
  );
}
