import React from "react";
import { Icon } from "../core/Icon.jsx";

const TONES = {
  info: { icon: "info", key: "info" },
  success: { icon: "circle-check", key: "success" },
  warning: { icon: "alert-triangle", key: "warning" },
  danger: { icon: "alert-octagon", key: "danger" },
};

export function Banner({ tone = "info", title, children, actions, correlationId, onDismiss, live, style, ...rest }) {
  const t = TONES[tone] || TONES.info;
  return (
    <div
      role={tone === "danger" ? "alert" : "status"}
      aria-live={live || (tone === "danger" ? "assertive" : "polite")}
      style={{
        display: "flex",
        gap: "var(--space-5)",
        padding: "var(--space-5) var(--space-6)",
        background: `var(--feedback-${t.key}-bg)`,
        border: `1px solid var(--feedback-${t.key}-border)`,
        borderRadius: "var(--radius-sm)",
        color: `var(--feedback-${t.key}-fg)`,
        ...style,
      }}
      {...rest}
    >
      <Icon name={t.icon} size={16} style={{ marginTop: 1 }} />
      <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
        {title && <p style={{ font: "var(--type-label)" }}>{title}</p>}
        {children && <div style={{ font: "var(--type-body-sm)", color: "var(--text-body)" }}>{children}</div>}
        {correlationId && (
          <p style={{ font: "var(--type-mono)", fontSize: "var(--text-xs)", color: "var(--text-muted)", userSelect: "all" }}>
            Reference {correlationId}
          </p>
        )}
        {actions && <div style={{ display: "flex", gap: "var(--space-4)", marginTop: "var(--space-2)" }}>{actions}</div>}
      </div>
      {onDismiss && (
        <button type="button" onClick={onDismiss} aria-label="Dismiss" style={{ background: "none", border: "none", padding: 0, cursor: "pointer", color: "inherit", height: 16 }}>
          <Icon name="x" size={14} />
        </button>
      )}
    </div>
  );
}
