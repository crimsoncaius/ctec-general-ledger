import type { CSSProperties, HTMLAttributes } from "react";
import {
  AlertCircle,
  AlertOctagon,
  CalendarRange,
  Check,
  ChevronDown,
  ChevronUp,
  ChevronsUpDown,
  Circle,
  CircleCheck,
  CircleDot,
  Clock,
  Copy,
  DatabaseZap,
  Download,
  Eye,
  FileStack,
  FileText,
  FlaskConical,
  Inbox,
  Info,
  LayoutDashboard,
  ListTree,
  ListChecks,
  Lock,
  LogIn,
  LogOut,
  Minus,
  PencilLine,
  Plus,
  RefreshCw,
  Scale,
  Search,
  SearchX,
  Settings,
  TableProperties,
  TriangleAlert,
  Undo2,
  UserCheck,
  Wrench,
  X,
  type LucideIcon,
} from "lucide-react";

const glyphs = {
  "alert-circle": AlertCircle,
  "alert-octagon": AlertOctagon,
  "alert-triangle": TriangleAlert,
  "calendar-range": CalendarRange,
  check: Check,
  "chevron-down": ChevronDown,
  "chevron-up": ChevronUp,
  "chevrons-up-down": ChevronsUpDown,
  circle: Circle,
  "circle-check": CircleCheck,
  "circle-dot": CircleDot,
  clock: Clock,
  copy: Copy,
  "database-zap": DatabaseZap,
  download: Download,
  eye: Eye,
  "file-stack": FileStack,
  "file-text": FileText,
  "flask-conical": FlaskConical,
  inbox: Inbox,
  info: Info,
  "layout-dashboard": LayoutDashboard,
  "list-checks": ListChecks,
  "list-tree": ListTree,
  lock: Lock,
  "log-in": LogIn,
  "log-out": LogOut,
  minus: Minus,
  "pencil-line": PencilLine,
  plus: Plus,
  "refresh-cw": RefreshCw,
  scale: Scale,
  search: Search,
  "search-x": SearchX,
  settings: Settings,
  "table-properties": TableProperties,
  "undo-2": Undo2,
  "user-check": UserCheck,
  wrench: Wrench,
  x: X,
} satisfies Record<string, LucideIcon>;

export type IconName = keyof typeof glyphs;

export interface IconProps extends Omit<HTMLAttributes<HTMLSpanElement>, "aria-hidden" | "aria-label" | "children"> {
  /** Approved Lucide glyph name in kebab-case. */
  name: IconName;
  /** Square pixel size. Use 14 in compact tables, 16 by default, and 20 in page headers. */
  size?: number;
  /** Accessible name. Omit for decorative icons; they are then hidden from assistive technology. */
  label?: string;
}

export function Icon({ name, size = 16, label, className, style, ...rest }: IconProps) {
  const Glyph = glyphs[name];
  const dimensions: CSSProperties = { width: size, height: size, ...style };

  return (
    <span
      {...rest}
      className={["ds-icon", className].filter(Boolean).join(" ")}
      role={label ? "img" : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
      style={dimensions}
    >
      <Glyph aria-hidden="true" focusable="false" size={size} strokeWidth={1.5} />
    </span>
  );
}
