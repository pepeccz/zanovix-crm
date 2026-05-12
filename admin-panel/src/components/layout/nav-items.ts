import {
  Building2,
  LayoutDashboard,
  Settings,
  UserCheck,
  UserCog,
  Users,
  Workflow,
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
  // Grupo trabajo
  {
    key: "nav.dashboard",
    href: "/dashboard",
    icon: LayoutDashboard,
    group: "trabajo",
  },
  {
    key: "nav.pipeline",
    href: "/pipeline",
    icon: Workflow,
    group: "trabajo",
  },
  {
    key: "nav.clients",
    href: "/clients",
    icon: Building2,
    group: "trabajo",
  },
  {
    key: "nav.leads",
    href: "/leads",
    icon: UserCheck,
    group: "trabajo",
  },
  // Grupo personas
  {
    key: "nav.team",
    href: "/team",
    icon: Users,
    group: "personas",
  },
  {
    key: "nav.users",
    href: "/users",
    icon: UserCog,
    group: "personas",
  },
  // Grupo recurrentes
  {
    key: "nav.settings",
    href: "/settings",
    icon: Settings,
    group: "recurrentes",
  },
];
