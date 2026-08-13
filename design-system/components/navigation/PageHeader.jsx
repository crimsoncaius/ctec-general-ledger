import React from "react";
import { Icon } from "../core/Icon.jsx";

export function PageHeader({ eyebrow, title, meta, actions, dataState, updatedAt, style, ...rest }) {
  const STATE = {
    current: { icon: "circle-check", text: "Current", color: "var(--green-600)" },
    loading: { icon: "loader", text: "Loading", color: "var(--text-muted)" },
    refreshing: { icon: "refresh-cw", text: "Refreshing", color: "var(--blue-600)" },
    stale: { icon: "clock", text: "Stale", color: "var(--amber-600)" },
    failed: { icon: "alert-triangle", text: "Load failed", color: "var(--red-600)" },
  }[dataState || "current"];
  return (
    <header
      style={{
        display: "flex",
        alignItems: "flex-start",
        justifyContent: "space-between",
        gap: "var(--space-8)",
        flexWrap: "wrap",
        padding: "var(--space-7) 0 var(--space-6)",
        ...style,
      }}
      {...rest}
    >
      <div style={{ minWidth: 0, display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
        {eyebrow && (
          <p style={{ font: "var(--type-overline)", letterSpacing: "var(--tracking-caps)", textTransform: "uppercase", color: "var(--text-muted)" }}>{eyebrow}</p>
        )}
        <h1 style={{ font: "var(--type-h1)", letterSpacing: "var(--tracking-tight)" }}>{title}</h1>
        {(meta || dataState) && (
          <div style={{ display: "flex", alignItems: "center", gap: "var(--space-5)", flexWrap: "wrap", font: "var(--type-caption)", color: "var(--text-muted)" }}>
            {meta}
            {dataState && (
              <span aria-live="polite" style={{ display: "inline-flex", alignItems: "center", gap: "var(--space-2)", color: STATE.color }}>
                <Icon name={STATE.icon} size={12} />
                {STATE.text}
                {updatedAt && <span style={{ color: "var(--text-muted)" }}>· {updatedAt}</span>}
              </span>
            )}
          </div>
        )}
      </div>
      {actions && <div style={{ display: "flex", gap: "var(--space-4)", flexWrap: "wrap" }}>{actions}</div>}
    </header>
  );
}
