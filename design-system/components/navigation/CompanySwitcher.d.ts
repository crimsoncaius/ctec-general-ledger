import * as React from "react";

export interface Membership {
  company: string;
  /** Company code — the short business identifier, always visible. */
  code: string;
  role: string;
}

/**
 * @startingPoint section="Navigation" subtitle="Active company, code, role and switcher" viewport="700x150"
 */
export interface CompanySwitcherProps extends React.HTMLAttributes<HTMLDivElement> {
  company: string;
  code: string;
  role?: string;
  /** Active memberships only. */
  memberships?: Membership[];
  onSelect?: (m: Membership) => void;
  /** True on the dark app header, false on light surfaces. */
  inverse?: boolean;
}

export declare function CompanySwitcher(props: CompanySwitcherProps): React.JSX.Element;
