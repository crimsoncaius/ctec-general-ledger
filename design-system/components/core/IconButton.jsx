import React from "react";
import { Icon } from "./Icon.jsx";

export function IconButton({ icon, label, size = "md", selected = false, disabled = false, style, ...rest }) {
  const [hover, setHover] = React.useState(false);
  const dim = size === "sm" ? "var(--control-h-sm)" : "var(--control-h)";
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      disabled={disabled}
      aria-pressed={selected || undefined}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        width: dim,
        height: dim,
        borderRadius: "var(--radius-sm)",
        border: "1px solid transparent",
        background: selected ? "var(--surface-selected)" : hover && !disabled ? "var(--surface-hover)" : "transparent",
        color: disabled ? "var(--text-muted)" : selected ? "var(--text-accent)" : "var(--text-secondary)",
        cursor: disabled ? "not-allowed" : "pointer",
        transition: "var(--transition-control)",
        ...style,
      }}
      {...rest}
    >
      <Icon name={icon} size={size === "sm" ? 14 : 16} />
    </button>
  );
}
