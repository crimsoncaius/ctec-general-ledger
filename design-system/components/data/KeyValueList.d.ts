import * as React from "react";

export interface KeyValueItem {
  label: string;
  value: React.ReactNode;
  /** Monospace value — identifiers, codes, timestamps. */
  mono?: boolean;
  numeric?: boolean;
}

export interface KeyValueListProps extends React.HTMLAttributes<HTMLDListElement> {
  items: KeyValueItem[];
  columns?: number;
}

export declare function KeyValueList(props: KeyValueListProps): React.JSX.Element;
