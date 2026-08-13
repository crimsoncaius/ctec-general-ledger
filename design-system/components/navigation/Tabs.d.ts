import * as React from "react";

export interface TabItem {
  id: string;
  label: string;
  icon?: string;
  count?: number | string;
}

export interface TabsProps extends React.HTMLAttributes<HTMLDivElement> {
  tabs: TabItem[];
  activeId: string;
  onChange?: (id: string) => void;
}

export declare function Tabs(props: TabsProps): React.JSX.Element;
