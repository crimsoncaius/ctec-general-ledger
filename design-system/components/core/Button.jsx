import React from "react";
import { Icon } from "./Icon.jsx";

const VARIANTS = {
  primary: { background: "var(--action-primary-bg)", color: "var(--action-primary-fg)", border: "1px solid var(--action-primary-bg)" },
  secondary: { background: "var(--action-secondary-bg)", color: "var(--action-secondary-fg)", border: "1px solid var(--border-input)" },
  ghost: { background: "transparent", color: "var(--text-secondary)", border: "1px solid transparent" },
  danger: { background: "var(--action-danger-bg)", color: "var(--action-danger-fg)", border: "1px solid var(--action-danger-bg)" },
};

const HOVER = {
  primary: "var(--action-primary-bg-hover)",
  secondary: "var(--surface-hover)",
  ghost: "var(--surface-hover)",
  danger: "var(--red-700)",
};

export function Button({
  variant = "secondary",
  size = "md",
  icon,
  iconAfter,
  busy = false,
  disabled = false,
  fullWidth = false,
  children,
  style,
  ...rest
}) {
  const [hover, setHover] = React.useState(false);
  const inert = disabled || busy;
  const base = VARIANTS[variant] || VARIANTS.secondary;
  const height = size === "sm" ? "var(--control-h-sm)" : size === "lg" ? "var(--control-h-lg)" : "var(--control-h)";
  return (
    <button
      type="button"
      disabled={inert}
      aria-busy={busy || undefined}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        gap: "var(--space-3)",
        height,
        width: fullWidth ? "100%" : undefined,
        padding: `0 ${size === "sm" ? "var(--space-4)" : "var(--control-pad-x)"}`,
        font: "var(--type-label)",
        letterSpacing: "var(--tracking-normal)",
        borderRadius: "var(--radius-sm)",
        cursor: inert ? "not-allowed" : "pointer",
        transition: "var(--transition-control)",
        whiteSpace: "nowrap",
        ...base,
        ...(hover && !inert ? { background: HOVER[variant] } : null),
        ...(inert ? { background: variant === "ghost" ? "transparent" : "var(--surface-disabled)", color: "var(--text-muted)", border: "1px solid var(--border-hairline)" } : null),
        ...style,
      }}
      {...rest}
    >
      {busy ? <Icon name="loader" size={14} /> : icon ? <Icon name={icon} size={14} /> : null}
      {children}
      {iconAfter ? <Icon name={iconAfter} size={14} /> : null}
    </button>
  );
}
