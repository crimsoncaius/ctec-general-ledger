import React from "react";
import { Icon } from "../core/Icon.jsx";

const STATES = {
  draft:      { label: "Draft", icon: "pencil-line", tone: "draft" },
  validated:  { label: "Validated", icon: "list-checks", tone: "validated" },
  approved:   { label: "Approved", icon: "user-check", tone: "approved" },
  posted:     { label: "Posted", icon: "lock", tone: "posted" },
  reversed:   { label: "Reversed", icon: "undo-2", tone: "draft" },
  open:       { label: "Open", icon: "circle-dot", tone: "validated" },
  closed:     { label: "Closed", icon: "lock", tone: "draft" },
  trial:      { label: "Trial", icon: "flask-conical", tone: "validated" },
  applied:    { label: "Applied", icon: "check", tone: "posted" },
  queued:     { label: "Queued", icon: "clock", tone: "draft" },
  running:    { label: "Running", icon: "loader", tone: "validated" },
  succeeded:  { label: "Succeeded", icon: "check", tone: "posted" },
  failed:     { label: "Failed", icon: "x", tone: "failed" },
  reconciled: { label: "Reconciled", icon: "scale", tone: "posted" },
  exception:  { label: "Exception", icon: "alert-triangle", tone: "failed" },
  compatible: { label: "Compatible", icon: "check", tone: "posted" },
  partial:    { label: "Partial", icon: "alert-triangle", tone: "approved" },
  manual:     { label: "Manual", icon: "wrench", tone: "failed" },
};

export function StatusPill({ status, label, size = "md", style, ...rest }) {
  const s = STATES[status] || { label: status, icon: "circle", tone: "draft" };
  const t = s.tone;
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "var(--space-2)",
        padding: size === "sm" ? "0 var(--space-3)" : "1px var(--space-4)",
        height: size === "sm" ? 18 : 21,
        background: `var(--status-${t}-bg)`,
        color: `var(--status-${t}-fg)`,
        border: `1px solid var(--status-${t}-border)`,
        borderRadius: "var(--radius-pill)",
        font: "var(--type-caption)",
        fontWeight: "var(--weight-medium)",
        whiteSpace: "nowrap",
        ...style,
      }}
      {...rest}
    >
      <Icon name={s.icon} size={11} />
      {label || s.label}
    </span>
  );
}
