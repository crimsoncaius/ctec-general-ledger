import * as React from "react";

export interface NavItem {
  id: string;
  label: string;
  icon: string;
  /** Pending-work count, e.g. drafts awaiting approval. */
  badge?: number | string;
  /** Viewable but not mutable with this capability set. */
  readOnly?: boolean;
}

export interface NavGroup {
  label: string;
  items: NavItem[];
}

export interface SidebarNavProps extends React.HTMLAttributes<HTMLElement> {
  /** Build this from the user's capabilities — omit destinations with none. */
  groups: NavGroup[];
  activeId?: string;
  onNavigate?: (id: string) => void;
  footer?: React.ReactNode;
}

export declare function SidebarNav(props: SidebarNavProps): React.JSX.Element;
