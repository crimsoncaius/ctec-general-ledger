import * as React from "react";

export interface DataTableColumn<Row = any> {
  key: string;
  header: React.ReactNode;
  /** Right-aligns and is the signal that the column holds a financial figure. */
  numeric?: boolean;
  align?: "left" | "center" | "right";
  /** Monospace body — codes, digests, identifiers. */
  mono?: boolean;
  /** Allow wrapping; default is nowrap with horizontal scroll. */
  wrap?: boolean;
  width?: string | number;
  render?: (row: Row, index: number) => React.ReactNode;
}

/**
 * @startingPoint section="Data" subtitle="Ledger table with sticky header and totals row" viewport="700x260"
 */
export interface DataTableProps<Row = any> extends React.HTMLAttributes<HTMLDivElement> {
  /** Required table caption. Visually hidden unless captionVisible. */
  caption: string;
  captionVisible?: boolean;
  columns: DataTableColumn<Row>[];
  rows: Row[];
  rowKey?: (row: Row, index: number) => React.Key;
  /** Empty-state content. Say whether there is no data or no match. */
  empty?: React.ReactNode;
  /** Totals row, keyed by column key. */
  footRow?: Record<string, React.ReactNode>;
  stickyHeader?: boolean;
  onRowClick?: (row: Row, index: number) => void;
}

export declare function DataTable<Row = any>(props: DataTableProps<Row>): React.JSX.Element;
export declare function SortHeader(props: { label: React.ReactNode; direction?: "asc" | "desc"; onClick?: () => void }): React.JSX.Element;
