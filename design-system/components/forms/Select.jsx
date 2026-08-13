import React from "react";
import { Icon } from "../core/Icon.jsx";

export function Select({ options = [], placeholder, invalid = false, disabled = false, style, ...rest }) {
  const [focus, setFocus] = React.useState(false);
  return (
    <div
      style={{
        position: "relative",
        display: "flex",
        alignItems: "center",
        height: "var(--control-h)",
        background: disabled ? "var(--surface-disabled)" : "var(--surface-card)",
        border: `1px solid ${invalid ? "var(--feedback-danger-border)" : focus ? "var(--border-focus)" : "var(--border-input)"}`,
        borderRadius: "var(--radius-sm)",
        boxShadow: focus ? "var(--focus-ring-tight)" : "none",
        transition: "var(--transition-control)",
        minWidth: 0,
        ...style,
      }}
    >
      <select
        disabled={disabled}
        aria-invalid={invalid || undefined}
        onFocus={() => setFocus(true)}
        onBlur={() => setFocus(false)}
        style={{
          appearance: "none",
          flex: 1,
          minWidth: 0,
          height: "100%",
          padding: "0 var(--space-8) 0 var(--space-4)",
          border: "none",
          outline: "none",
          background: "transparent",
          color: "var(--text-body)",
          font: "var(--type-body-sm)",
          cursor: disabled ? "not-allowed" : "pointer",
        }}
        {...rest}
      >
        {placeholder && <option value="">{placeholder}</option>}
        {options.map((o) => {
          const opt = typeof o === "string" ? { value: o, label: o } : o;
          return (
            <option key={opt.value} value={opt.value} disabled={opt.disabled}>
              {opt.label}
            </option>
          );
        })}
      </select>
      <Icon name="chevron-down" size={14} style={{ position: "absolute", right: "var(--space-4)", color: "var(--text-muted)", pointerEvents: "none" }} />
    </div>
  );
}
