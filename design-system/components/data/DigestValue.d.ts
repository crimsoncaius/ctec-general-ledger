import * as React from "react";

export interface DigestValueProps extends React.HTMLAttributes<HTMLSpanElement> {
  /** The full 64-character content or source digest. Never pass a shortened value. */
  value: string;
  /** Used in the copy button's accessible name. Default "Digest". */
  label?: string;
  /** Middle-elide the display. The full value stays copyable and in the title. */
  truncate?: boolean;
}

export declare function DigestValue(props: DigestValueProps): React.JSX.Element;
