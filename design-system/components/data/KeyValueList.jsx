import React from "react";

export function KeyValueList({ items = [], columns = 1, style, ...rest }) {
  return (
    <dl
      style={{
        display: "grid",
        gridTemplateColumns: columns > 1 ? `repeat(auto-fit, minmax(150px, 1fr))` : "minmax(0, 1fr)",
        maxWidth: columns > 1 ? undefined : "100%",
        gap: "var(--space-5) var(--space-9)",
        margin: 0,
        ...style,
      }}
      {...rest}
    >
      {items.map((it) => (
        <div key={it.label} style={{ minWidth: 0, display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
          <dt style={{ font: "var(--type-overline)", letterSpacing: "var(--tracking-caps)", textTransform: "uppercase", color: "var(--text-muted)" }}>
            {it.label}
          </dt>
          <dd
            data-numeric={it.numeric ? "" : undefined}
            style={{
              margin: 0,
              font: it.mono ? "var(--type-mono)" : "var(--type-body)",
              color: "var(--text-body)",
              overflowWrap: "anywhere",
            }}
          >
            {it.value}
          </dd>
        </div>
      ))}
    </dl>
  );
}
