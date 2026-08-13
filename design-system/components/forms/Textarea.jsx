import React from "react";

export function Textarea({ invalid = false, rows = 3, mono = false, style, ...rest }) {
  const [focus, setFocus] = React.useState(false);
  return (
    <textarea
      rows={rows}
      aria-invalid={invalid || undefined}
      onFocus={() => setFocus(true)}
      onBlur={() => setFocus(false)}
      style={{
        width: "100%",
        padding: "var(--space-4)",
        background: "var(--surface-card)",
        color: "var(--text-body)",
        font: mono ? "var(--type-mono)" : "var(--type-body-sm)",
        border: `1px solid ${invalid ? "var(--feedback-danger-border)" : focus ? "var(--border-focus)" : "var(--border-input)"}`,
        borderRadius: "var(--radius-sm)",
        boxShadow: focus ? "var(--focus-ring-tight)" : "none",
        outline: "none",
        resize: "vertical",
        transition: "var(--transition-control)",
        ...style,
      }}
      {...rest}
    />
  );
}
