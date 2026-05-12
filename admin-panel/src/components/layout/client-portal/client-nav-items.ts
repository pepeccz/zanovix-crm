import {
  BarChart3,
  FileText,
  LayoutDashboard,
  MessageSquare,
  ReceiptText,
  CalendarDays,
  Headphones,
  FolderOpen,
  type LucideIcon,
} from "lucide-react";

export interface ClientNavItem {
  key: string;
  href: string;
  icon: LucideIcon;
}

export const CLIENT_NAV_ITEMS: ClientNavItem[] = [
  {
    key: "sidebar.client.dashboard",
    href: "/client",
    icon: LayoutDashboard,
  },
  {
    key: "sidebar.client.diagnostic",
    href: "/client/diagnostic",
    icon: BarChart3,
  },
  {
    key: "sidebar.client.projects",
    href: "/client/projects",
    icon: FolderOpen,
  },
  {
    key: "sidebar.client.billing",
    href: "/client/billing",
    icon: ReceiptText,
  },
  {
    key: "sidebar.client.documents",
    href: "/client/documents",
    icon: FileText,
  },
  {
    key: "sidebar.client.chat",
    href: "/client/chat",
    icon: MessageSquare,
  },
  {
    key: "sidebar.client.meetings",
    href: "/client/meetings",
    icon: CalendarDays,
  },
  {
    key: "sidebar.client.support",
    href: "/client/support",
    icon: Headphones,
  },
];
