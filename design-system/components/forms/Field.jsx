import React from "react";
import { Icon } from "../core/Icon.jsx";

export function Field({ label, htmlFor, hint, error, required = false, immutable = false, children, style, ...rest }) {
  const describedBy = [];
  if (hint) describedBy.push(`${htmlFor}-hint`);
  if (error) describedBy.push(`${htmlFor}-error`);
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)", minWidth: 0, ...style }} {...rest}>
      <label htmlFor={htmlFor} style={{ font: "var(--type-label)", color: "var(--text-body)", display: "flex", gap: "var(--space-3)", alignItems: "baseline" }}>
        {label}
        {required && <span style={{ color: "var(--text-muted)", font: "var(--type-caption)" }}>required</span>}
        {immutable && (
          <span style={{ color: "var(--text-muted)", font: "var(--type-caption)", display: "inline-flex", gap: 3, alignItems: "center" }}>
            <Icon name="lock" size={11} /> fixed after creation
          </span>
        )}
      </label>
      {React.Children.map(children, (child) =>
        React.isValidElement(child)
          ? React.cloneElement(child, {
              id: child.props.id || htmlFor,
              invalid: child.props.invalid ?? Boolean(error),
              "aria-describedby": describedBy.join(" ") || undefined,
            })
          : child
      )}
      {hint && !error && (
        <p id={`${htmlFor}-hint`} style={{ font: "var(--type-caption)", color: "var(--text-muted)" }}>{hint}</p>
      )}
      {error && (
        <p id={`${htmlFor}-error`} style={{ font: "var(--type-caption)", color: "var(--feedback-danger-fg)", display: "flex", gap: "var(--space-2)", alignItems: "flex-start" }}>
          <Icon name="alert-circle" size={12} style={{ marginTop: 1 }} /> {error}
        </p>
      )}
    </div>
  );
}
