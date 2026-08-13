import * as React from "react";

/**
 * @startingPoint section="Layout" subtitle="Titled panel with actions and evidence footer" viewport="700x220"
 */
export interface CardProps extends React.HTMLAttributes<HTMLElement> {
  title?: React.ReactNode;
  description?: React.ReactNode;
  /** Header-right controls — usually Buttons or an IconButton. */
  actions?: React.ReactNode;
  /** Sunken strip for evidence: digests, run times, row counts. */
  footer?: React.ReactNode;
  /** Set false when the body is a full-bleed DataTable. */
  padded?: boolean;
}

export declare function Card(props: CardProps): React.JSX.Element;
