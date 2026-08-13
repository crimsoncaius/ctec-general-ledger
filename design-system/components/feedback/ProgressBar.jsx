import React from "react";
import { StatusPill } from "../data/StatusPill.jsx";

export function ProgressBar({ value = 0, status = "running", label, indeterminate = false, style, ...rest }) {
  const pct = Math.max(0, Math.min(100, value));
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)", minWidth: 0, ...style }} {...rest}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "var(--space-5)" }}>
        <span style={{ font: "var(--type-label)", color: "var(--text-body)" }}>{label}</span>
        <span style={{ display: "inline-flex", alignItems: "center", gap: "var(--space-4)" }}>
          <StatusPill status={status} size="sm" />
          {!indeterminate && <span data-numeric="" style={{ font: "var(--type-amount)", color: "var(--text-secondary)" }}>{pct}%</span>}
        </span>
      </div>
      <div
        role="progressbar"
        aria-valuenow={indeterminate ? undefined : pct}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={label}
        style={{ height: 5, background: "var(--n-100)", borderRadius: "var(--radius-pill)", overflow: "hidden" }}
      >
        <div
          style={{
            height: "100%",
            width: indeterminate ? "35%" : `${pct}%`,
            background: status === "failed" ? "var(--red-600)" : status === "succeeded" ? "var(--green-600)" : "var(--blue-500)",
            borderRadius: "var(--radius-pill)",
            transition: `width var(--duration-slow) var(--ease-out)`,
          }}
        />
      </div>
    </div>
  );
}
