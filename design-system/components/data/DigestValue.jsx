import React from "react";
import { Icon } from "../core/Icon.jsx";

export function DigestValue({ value, label = "Digest", truncate = false, style, ...rest }) {
  const [copied, setCopied] = React.useState(false);
  const shown = truncate ? `${value.slice(0, 12)}…${value.slice(-8)}` : value;
  const copy = () => {
    if (navigator.clipboard) navigator.clipboard.writeText(value);
    setCopied(true);
    setTimeout(() => setCopied(false), 1600);
  };
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: "var(--space-3)", minWidth: 0, ...style }} {...rest}>
      <code
        title={value}
        style={{
          font: "var(--type-mono)",
          fontSize: "var(--text-xs)",
          color: "var(--text-secondary)",
          background: "var(--surface-sunken)",
          border: "1px solid var(--border-hairline)",
          borderRadius: "var(--radius-xs)",
          padding: "1px var(--space-3)",
          userSelect: "all",
          overflowWrap: "anywhere",
        }}
      >
        {shown}
      </code>
      <button
        type="button"
        onClick={copy}
        aria-label={`Copy ${label.toLowerCase()}`}
        style={{ display: "inline-flex", alignItems: "center", gap: 3, background: "none", border: "none", padding: 0, cursor: "pointer", color: "var(--text-link)", font: "var(--type-caption)" }}
      >
        <Icon name={copied ? "check" : "copy"} size={12} />
        {copied ? "Copied" : "Copy"}
      </button>
    </span>
  );
}
