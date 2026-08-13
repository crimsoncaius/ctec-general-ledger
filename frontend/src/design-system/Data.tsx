import { useState, type HTMLAttributes, type Key, type ReactNode } from "react";
import { Icon } from "./Icon";

export interface DataTableColumn<Row> {
  key: string;
  header: ReactNode;
  numeric?: boolean;
  align?: "left" | "center" | "right";
  mono?: boolean;
  wrap?: boolean;
  width?: string | number;
  render?: (row: Row, index: number) => ReactNode;
}
export interface DataTableProps<Row> extends HTMLAttributes<HTMLDivElement> {
  caption: string;
  captionVisible?: boolean;
  columns: DataTableColumn<Row>[];
  rows: Row[];
  rowKey?: (row: Row, index: number) => Key;
  empty?: ReactNode;
  footRow?: Record<string, ReactNode>;
  stickyHeader?: boolean;
  onRowClick?: (row: Row, index: number) => void;
}

export function DataTable<Row extends Record<string, unknown>>({ caption, captionVisible = false, columns, rows, rowKey = (_row, index) => index, empty, footRow, stickyHeader = true, onRowClick, className, ...rest }: DataTableProps<Row>) {
  return <div className={["ds-table-wrap", stickyHeader ? "ds-table-wrap--sticky" : "", className].filter(Boolean).join(" ")} {...rest}>
    <table className="ds-table">
      <caption className={captionVisible ? "ds-table__caption" : "ds-visually-hidden"}>{caption}</caption>
      <thead><tr>{columns.map((column) => <th key={column.key} scope="col" className={[column.numeric ? "is-numeric" : "", column.align ? `is-${column.align}` : ""].filter(Boolean).join(" ")} style={{ width: column.width }}>{column.header}</th>)}</tr></thead>
      <tbody>
        {!rows.length ? <tr><td colSpan={columns.length} className="ds-table__empty">{empty ?? "No records."}</td></tr> : null}
        {rows.map((row, index) => <tr key={rowKey(row, index)} onClick={onRowClick ? () => onRowClick(row, index) : undefined} tabIndex={onRowClick ? 0 : undefined} className={onRowClick ? "is-clickable" : ""} onKeyDown={onRowClick ? (event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); onRowClick(row, index); } } : undefined}>
          {columns.map((column) => <td key={column.key} className={[column.numeric ? "is-numeric" : "", column.align ? `is-${column.align}` : "", column.mono ? "is-mono" : "", column.wrap ? "is-wrap" : ""].filter(Boolean).join(" ")}>{column.render ? column.render(row, index) : row[column.key] as ReactNode}</td>)}
        </tr>)}
      </tbody>
      {footRow ? <tfoot><tr>{columns.map((column) => <td key={column.key} className={column.numeric ? "is-numeric" : ""}>{footRow[column.key]}</td>)}</tr></tfoot> : null}
    </table>
  </div>;
}

export function SortHeader({ label, direction, onClick }: { label: ReactNode; direction?: "asc" | "desc"; onClick?: () => void }) {
  return <button type="button" className="ds-sort-header" onClick={onClick}>{label}<Icon name={direction === "desc" ? "chevron-down" : "chevron-up"} size={11} /></button>;
}

export interface AmountCellProps extends HTMLAttributes<HTMLSpanElement> { value: number | string | null; currency?: string; side?: "debit" | "credit"; zeroAs?: string; emphasis?: boolean }
export function AmountCell({ value, currency, side, zeroAs = "—", emphasis = false, className, ...rest }: AmountCellProps) {
  const raw = value == null ? "" : String(value).trim();
  const numericValue = typeof value === "number" ? value : Number(raw.replaceAll(",", ""));
  const isZero = value == null || raw === "" || (!Number.isNaN(numericValue) && numericValue === 0);
  const negative = !isZero && (typeof value === "number" ? value < 0 : raw.startsWith("-"));
  let shown = zeroAs;
  if (!isZero) {
    if (typeof value === "number") shown = Math.abs(value).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    else shown = raw.replace(/^-/, "");
  }
  return <span data-numeric="" data-side={side} className={["ds-amount", emphasis ? "ds-amount--emphasis" : "", isZero ? "is-zero" : "", className].filter(Boolean).join(" ")} {...rest}><span>{negative ? `(${shown})` : shown}</span>{currency && !isZero ? <span className="ds-amount__currency">{currency}</span> : null}</span>;
}

export type LedgerStatus = "draft" | "validated" | "approved" | "posted" | "reversed" | "open" | "closed" | "trial" | "applied" | "queued" | "running" | "succeeded" | "failed" | "reconciled" | "exception" | "compatible" | "partial" | "manual";
const STATUS = {
  draft: ["Draft", "pencil-line", "draft"], validated: ["Validated", "list-checks", "validated"], approved: ["Approved", "user-check", "approved"], posted: ["Posted", "lock", "posted"], reversed: ["Reversed", "undo-2", "draft"], open: ["Open", "circle-dot", "validated"], closed: ["Closed", "lock", "draft"], trial: ["Trial", "flask-conical", "validated"], applied: ["Applied", "check", "posted"], queued: ["Queued", "clock", "draft"], running: ["Running", "refresh-cw", "validated"], succeeded: ["Succeeded", "check", "posted"], failed: ["Failed", "x", "failed"], reconciled: ["Reconciled", "scale", "posted"], exception: ["Exception", "alert-triangle", "failed"], compatible: ["Compatible", "check", "posted"], partial: ["Partial", "alert-triangle", "approved"], manual: ["Manual", "wrench", "failed"],
} as const;
export function StatusPill({ status, label, size = "md", className, ...rest }: HTMLAttributes<HTMLSpanElement> & { status: LedgerStatus; label?: string; size?: "sm" | "md" }) {
  const [defaultLabel, icon, tone] = STATUS[status];
  return <span className={["ds-status", `ds-status--${tone}`, `ds-status--${size}`, className].filter(Boolean).join(" ")} {...rest}><Icon name={icon} size={11} />{label ?? defaultLabel}</span>;
}

export function DigestValue({ value, label = "Digest", truncate = false, className, ...rest }: HTMLAttributes<HTMLSpanElement> & { value: string; label?: string; truncate?: boolean }) {
  const [copied, setCopied] = useState(false);
  const shown = truncate && value.length > 24 ? `${value.slice(0, 12)}…${value.slice(-8)}` : value;
  async function copy() { await navigator.clipboard?.writeText(value); setCopied(true); window.setTimeout(() => setCopied(false), 1600); }
  return <span className={["ds-digest", className].filter(Boolean).join(" ")} {...rest}><code title={value}>{shown}</code><button type="button" onClick={() => void copy()} aria-label={`Copy ${label.toLowerCase()}`}><Icon name={copied ? "check" : "copy"} size={12} />{copied ? "Copied" : "Copy"}</button></span>;
}

export interface KeyValueItem { label: string; value: ReactNode; mono?: boolean; numeric?: boolean }
export function KeyValueList({ items, columns = 1, className, ...rest }: HTMLAttributes<HTMLDListElement> & { items: KeyValueItem[]; columns?: number }) {
  return <dl className={["ds-key-values", className].filter(Boolean).join(" ")} style={{ "--key-value-columns": columns } as React.CSSProperties} {...rest}>{items.map((item) => <div key={item.label}><dt>{item.label}</dt><dd className={item.mono ? "is-mono" : ""} data-numeric={item.numeric ? "" : undefined}>{item.value}</dd></div>)}</dl>;
}
