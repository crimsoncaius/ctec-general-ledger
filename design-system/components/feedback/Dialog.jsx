import React from "react";
import { Icon } from "../core/Icon.jsx";
import { Button } from "../core/Button.jsx";

export function Dialog({ open = true, title, subject, consequence, tone = "neutral", confirmLabel = "Confirm", confirmWord, cancelLabel = "Cancel", busy = false, onConfirm, onCancel, children, style, ...rest }) {
  const [typed, setTyped] = React.useState("");
  const ref = React.useRef(null);
  React.useEffect(() => { if (open && ref.current) ref.current.focus(); }, [open]);
  if (!open) return null;
  const gated = confirmWord ? typed.trim().toUpperCase() !== confirmWord.toUpperCase() : false;
  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(23,27,34,0.44)", display: "grid", placeItems: "center", padding: "var(--space-8)", zIndex: 60 }}>
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="dlg-title"
        ref={ref}
        tabIndex={-1}
        style={{
          width: "min(520px, 100%)",
          background: "var(--surface-raised)",
          borderRadius: "var(--radius-md)",
          boxShadow: "var(--shadow-dialog)",
          outline: "none",
          ...style,
        }}
        {...rest}
      >
        <header style={{ display: "flex", gap: "var(--space-5)", padding: "var(--space-7) var(--space-8) var(--space-5)" }}>
          {tone === "danger" && <Icon name="alert-octagon" size={18} style={{ color: "var(--feedback-danger-fg)", marginTop: 2 }} />}
          <div style={{ minWidth: 0 }}>
            <h2 id="dlg-title" style={{ font: "var(--type-h3)" }}>{title}</h2>
            {subject && <p style={{ font: "var(--type-mono)", fontSize: "var(--text-sm)", color: "var(--text-secondary)", marginTop: "var(--space-3)" }}>{subject}</p>}
          </div>
        </header>
        <div style={{ padding: "0 var(--space-8)", display: "flex", flexDirection: "column", gap: "var(--space-5)" }}>
          {consequence && <p style={{ font: "var(--type-body-sm)", color: "var(--text-body)" }}>{consequence}</p>}
          {children}
          {confirmWord && (
            <label style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)", font: "var(--type-label)" }}>
              Type {confirmWord} to continue
              <input
                value={typed}
                onChange={(e) => setTyped(e.target.value)}
                style={{ height: "var(--control-h)", padding: "0 var(--space-4)", font: "var(--type-mono)", border: "1px solid var(--border-input)", borderRadius: "var(--radius-sm)", outline: "none" }}
              />
            </label>
          )}
        </div>
        <footer style={{ display: "flex", justifyContent: "flex-end", gap: "var(--space-4)", padding: "var(--space-7) var(--space-8)" }}>
          <Button variant="ghost" onClick={onCancel}>{cancelLabel}</Button>
          <Button variant={tone === "danger" ? "danger" : "primary"} disabled={gated} busy={busy} onClick={onConfirm}>{confirmLabel}</Button>
        </footer>
      </div>
    </div>
  );
}
