import React from "react";

export function Switch({ checked = false, label, disabled = false, onChange, style, ...rest }) {
  return (
    <label style={{ display: "inline-flex", gap: "var(--space-4)", alignItems: "center", cursor: disabled ? "not-allowed" : "pointer", ...style }}>
      <span style={{ position: "relative", display: "inline-flex", width: 32, height: 18, flex: "0 0 auto" }}>
        <input
          type="checkbox"
          role="switch"
          checked={checked}
          disabled={disabled}
          onChange={onChange}
          style={{ position: "absolute", inset: 0, margin: 0, opacity: 0, cursor: "inherit" }}
          {...rest}
        />
        <span
          aria-hidden="true"
          style={{
            width: 32,
            height: 18,
            borderRadius: "var(--radius-pill)",
            background: disabled ? "var(--surface-disabled)" : checked ? "var(--blue-500)" : "var(--n-300)",
            transition: "var(--transition-control)",
            position: "relative",
          }}
        >
          <span
            style={{
              position: "absolute",
              top: 2,
              left: checked ? 16 : 2,
              width: 14,
              height: 14,
              borderRadius: "var(--radius-pill)",
              background: "var(--n-0)",
              boxShadow: "var(--shadow-raised)",
              transition: `left var(--duration-fast) var(--ease-standard)`,
            }}
          />
        </span>
      </span>
      {label && <span style={{ font: "var(--type-body-sm)", color: disabled ? "var(--text-muted)" : "var(--text-body)" }}>{label}</span>}
    </label>
  );
}
