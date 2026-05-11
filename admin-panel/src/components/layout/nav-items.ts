import {
  LayoutDashboard,
  UserCheck,
  Users,
  Settings,
  type LucideIcon,
} from "lucide-react";

export type NavGroup = "trabajo" | "personas" | "recurrentes";

export interface NavItem {
  key: string;
  href: string;
  icon: LucideIcon;
  group: NavGroup;
}

export const NAV_ITEMS: NavItem[] = [
  {
    key: "nav.dashboard",
    href: "/dashboard",
    icon: LayoutDashboard,
    group: "trabajo",
  },
  {
    key: "nav.clients",
    href: "/leads",
    icon: UserCheck,
    group: "trabajo",
  },
  {
    key: "nav.team",
    href: "/users",
    icon: Users,
    group: "personas",
  },
  {
    key: "nav.settings",
    href: "/settings",
    icon: Settings,
    group: "recurrentes",
  },
];
