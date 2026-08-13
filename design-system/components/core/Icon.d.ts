import * as React from "react";

export interface IconProps extends React.HTMLAttributes<HTMLSpanElement> {
  /** Lucide icon name in kebab-case, e.g. "circle-check", "chevron-down". */
  name: string;
  /** Square pixel size. 14 in compact tables, 16 default, 20 in page headers. */
  size?: number;
  /** Accessible name. Omit for decorative icons — they are then aria-hidden. */
  label?: string;
}

export declare function Icon(props: IconProps): React.JSX.Element;
