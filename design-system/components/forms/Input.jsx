import React from "react";

export function Input({ invalid = false, numeric = false, prefix, suffix, disabled = false, style, ...rest }) {
  const [focus, setFocus] = React.useState(false);
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: "var(--space-3)",
        height: "var(--control-h)",
        padding: "0 var(--space-4)",
        background: disabled ? "var(--surface-disabled)" : "var(--surface-card)",
        border: `1px solid ${invalid ? "var(--feedback-danger-border)" : focus ? "var(--border-focus)" : "var(--border-input)"}`,
        borderRadius: "var(--radius-sm)",
        boxShadow: focus ? "var(--focus-ring-tight)" : "none",
        transition: "var(--transition-control)",
        minWidth: 0,
        ...style,
      }}
    >
      {prefix && <span style={{ font: "var(--type-caption)", color: "var(--text-muted)" }}>{prefix}</span>}
      <input
        disabled={disabled}
        aria-invalid={invalid || undefined}
        onFocus={() => setFocus(true)}
        onBlur={() => setFocus(false)}
        style={{
          flex: 1,
          minWidth: 0,
          border: "none",
          outline: "none",
          background: "transparent",
          color: "var(--text-body)",
          font: numeric ? "var(--type-amount)" : "var(--type-body-sm)",
          fontVariantNumeric: numeric ? "tabular-nums" : undefined,
          textAlign: numeric ? "right" : "left",
        }}
        {...rest}
      />
      {suffix && <span style={{ font: "var(--type-caption)", color: "var(--text-muted)" }}>{suffix}</span>}
    </div>
  );
}
