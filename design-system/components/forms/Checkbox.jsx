import React from "react";
import { Icon } from "../core/Icon.jsx";

export function Checkbox({ label, description, checked, indeterminate = false, disabled = false, onChange, style, ...rest }) {
  const ref = React.useRef(null);
  React.useEffect(() => { if (ref.current) ref.current.indeterminate = indeterminate; }, [indeterminate]);
  const on = checked || indeterminate;
  return (
    <label style={{ display: "inline-flex", gap: "var(--space-4)", alignItems: "flex-start", cursor: disabled ? "not-allowed" : "pointer", ...style }}>
      <span style={{ position: "relative", display: "inline-flex", width: 15, height: 15, marginTop: 1, flex: "0 0 auto" }}>
        <input
          ref={ref}
          type="checkbox"
          checked={Boolean(checked)}
          disabled={disabled}
          onChange={onChange}
          style={{ position: "absolute", inset: 0, margin: 0, opacity: 0, cursor: "inherit" }}
          {...rest}
        />
        <span
          aria-hidden="true"
          style={{
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            width: 15,
            height: 15,
            borderRadius: "var(--radius-xs)",
            border: `1px solid ${on ? "var(--blue-500)" : "var(--border-input)"}`,
            background: disabled ? "var(--surface-disabled)" : on ? "var(--blue-500)" : "var(--surface-card)",
            color: "var(--n-0)",
            transition: "var(--transition-control)",
          }}
        >
          {indeterminate ? <Icon name="minus" size={11} /> : checked ? <Icon name="check" size={11} /> : null}
        </span>
      </span>
      {(label || description) && (
        <span style={{ minWidth: 0 }}>
          <span style={{ font: "var(--type-body-sm)", color: disabled ? "var(--text-muted)" : "var(--text-body)" }}>{label}</span>
          {description && <span style={{ display: "block", font: "var(--type-caption)", color: "var(--text-muted)" }}>{description}</span>}
        </span>
      )}
    </label>
  );
}
