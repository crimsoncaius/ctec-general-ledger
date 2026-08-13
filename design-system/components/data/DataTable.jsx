import React from "react";
import { Icon } from "../core/Icon.jsx";

export function DataTable({ caption, captionVisible = false, columns = [], rows = [], rowKey = (r, i) => i, empty, footRow, stickyHeader = true, onRowClick, style, ...rest }) {
  const align = (c) => (c.numeric ? "right" : c.align || "left");
  return (
    <div style={{ overflowX: "auto", minWidth: 0, ...style }} {...rest}>
      <table style={{ width: "100%", borderCollapse: "collapse", font: "var(--type-body-sm)" }}>
        <caption
          style={
            captionVisible
              ? { textAlign: "left", font: "var(--type-label)", color: "var(--text-secondary)", padding: "var(--space-4) var(--row-pad-x)" }
              : { position: "absolute", width: 1, height: 1, overflow: "hidden", clip: "rect(0 0 0 0)", whiteSpace: "nowrap" }
          }
        >
          {caption}
        </caption>
        <thead>
          <tr>
            {columns.map((c) => (
              <th
                key={c.key}
                scope="col"
                style={{
                  position: stickyHeader ? "sticky" : undefined,
                  top: stickyHeader ? 0 : undefined,
                  zIndex: 1,
                  textAlign: align(c),
                  padding: "var(--space-4) var(--row-pad-x)",
                  background: "var(--surface-sunken)",
                  borderBottom: "1px solid var(--border-strong)",
                  boxShadow: stickyHeader ? "var(--shadow-sticky)" : undefined,
                  font: "var(--type-overline)",
                  letterSpacing: "var(--tracking-caps)",
                  textTransform: "uppercase",
                  color: "var(--text-secondary)",
                  whiteSpace: "nowrap",
                  width: c.width,
                }}
              >
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 && (
            <tr>
              <td colSpan={columns.length} style={{ padding: "var(--space-9) var(--row-pad-x)", textAlign: "center", color: "var(--text-muted)", font: "var(--type-body-sm)" }}>
                {empty || "No records."}
              </td>
            </tr>
          )}
          {rows.map((r, i) => (
            <tr
              key={rowKey(r, i)}
              onClick={onRowClick ? () => onRowClick(r, i) : undefined}
              tabIndex={onRowClick ? 0 : undefined}
              style={{
                height: "var(--row-h)",
                cursor: onRowClick ? "pointer" : undefined,
                background: r.selected ? "var(--surface-selected)" : "transparent",
              }}
            >
              {columns.map((c) => (
                <td
                  key={c.key}
                  style={{
                    textAlign: align(c),
                    padding: "var(--row-pad-y) var(--row-pad-x)",
                    borderBottom: "1px solid var(--border-table)",
                    color: "var(--text-body)",
                    font: c.mono ? "var(--type-mono)" : "inherit",
                    whiteSpace: c.wrap ? "normal" : "nowrap",
                    verticalAlign: "middle",
                  }}
                >
                  {c.render ? c.render(r, i) : r[c.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
        {footRow && (
          <tfoot>
            <tr style={{ height: "var(--row-h)" }}>
              {columns.map((c) => (
                <td
                  key={c.key}
                  style={{
                    textAlign: align(c),
                    padding: "var(--row-pad-y) var(--row-pad-x)",
                    borderTop: "1px solid var(--border-strong)",
                    background: "var(--surface-sunken)",
                    font: "var(--type-label)",
                  }}
                >
                  {footRow[c.key]}
                </td>
              ))}
            </tr>
          </tfoot>
        )}
      </table>
    </div>
  );
}

export function SortHeader({ label, direction, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      style={{ display: "inline-flex", alignItems: "center", gap: 4, background: "none", border: "none", padding: 0, font: "inherit", color: "inherit", letterSpacing: "inherit", textTransform: "inherit", cursor: "pointer" }}
    >
      {label}
      <Icon name={direction === "desc" ? "chevron-down" : "chevron-up"} size={11} style={{ opacity: direction ? 1 : 0.3 }} />
    </button>
  );
}
