"use client";

import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import {
  Users,
  LayoutDashboard,
  Settings,
  LogOut,
  ChevronLeft,
  ChevronRight,
  UserCheck,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import { useAuth } from "@/contexts/auth-context";
import { useSidebar } from "@/contexts/sidebar-context";

interface NavItem {
  title: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
}

const mainNav: NavItem[] = [
  {
    title: "Dashboard",
    href: "/dashboard",
    icon: LayoutDashboard,
  },
  {
    title: "Leads",
    href: "/leads",
    icon: UserCheck,
  },
];

const systemNav: NavItem[] = [
  {
    title: "Usuarios",
    href: "/users",
    icon: Users,
  },
  {
    title: "Configuración",
    href: "/settings",
    icon: Settings,
  },
];

// ---------------------------------------------------------------------------
// NavSection — renders a group of nav links
// ---------------------------------------------------------------------------

function NavSection({
  title,
  items,
  isCollapsed,
  onNavClick,
}: {
  title: string;
  items: NavItem[];
  isCollapsed: boolean;
  onNavClick?: () => void;
}) {
  const pathname = usePathname();

  return (
    <div className={cn("py-2", isCollapsed ? "px-2" : "px-3")}>
      {!isCollapsed && (
        <h2 className="mb-2 px-4 text-xs font-semibold tracking-tight text-muted-foreground uppercase">
          {title}
        </h2>
      )}
      <div className="space-y-1">
        {items.map((item) => {
          const Icon = item.icon;
          const isActive =
            pathname === item.href || pathname.startsWith(item.href + "/");

          return (
            <TooltipProvider key={item.href} delayDuration={0}>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Link href={item.href} onClick={onNavClick}>
                    <Button
                      variant={isActive ? "secondary" : "ghost"}
                      className={cn(
                        "w-full relative",
                        isCollapsed ? "justify-center px-2" : "justify-start",
                        isActive &&
                          "bg-sidebar-accent text-sidebar-accent-foreground"
                      )}
                    >
                      <Icon
                        className={cn("h-4 w-4", !isCollapsed && "mr-2")}
                      />
                      {!isCollapsed && (
                        <span className="truncate flex-1 text-left">
                          {item.title}
                        </span>
                      )}
                    </Button>
                  </Link>
                </TooltipTrigger>
                {isCollapsed && (
                  <TooltipContent side="right">{item.title}</TooltipContent>
                )}
              </Tooltip>
            </TooltipProvider>
          );
        })}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// SidebarInner — shared content rendered both in desktop inline mode and
// inside the mobile Sheet drawer
// ---------------------------------------------------------------------------

interface SidebarInnerProps {
  isCollapsed: boolean;
  displayName: string;
  roleLabel: string;
  onLogout: () => void;
  onNavClick?: () => void;
}

function SidebarInner({
  isCollapsed,
  displayName,
  roleLabel,
  onLogout,
  onNavClick,
}: SidebarInnerProps) {
  return (
    <>
      {/* Logo/Brand */}
      <div className="flex h-16 items-center border-b px-3">
        <Link
          href="/dashboard"
          onClick={onNavClick}
          className={cn(
            "flex items-center gap-2 overflow-hidden",
            isCollapsed && "justify-center"
          )}
        >
          <Image
            src="/logo.png"
            width={isCollapsed ? 40 : 120}
            height={isCollapsed ? 40 : 40}
            alt="Zanovix CRM"
            className="flex-shrink-0 object-contain"
          />
        </Link>
      </div>

      {/* Navigation */}
      <div className="flex-1 overflow-y-auto py-4">
        <NavSection
          title="Principal"
          items={mainNav}
          isCollapsed={isCollapsed}
          onNavClick={onNavClick}
        />
        <Separator className="my-2" />
        <NavSection
          title="Sistema"
          items={systemNav}
          isCollapsed={isCollapsed}
          onNavClick={onNavClick}
        />
      </div>

      {/* Powered by Zanovix */}
      <div className={cn("px-3 py-2", isCollapsed && "px-2")}>
        <a
          href="https://zanovix.com"
          target="_blank"
          rel="noopener noreferrer"
          className={cn(
            "flex items-center text-xs text-muted-foreground hover:text-foreground transition-colors",
            "justify-center"
          )}
        >
          {isCollapsed ? (
            <TooltipProvider delayDuration={0}>
              <Tooltip>
                <TooltipTrigger asChild>
                  <span className="font-medium">Z</span>
                </TooltipTrigger>
                <TooltipContent side="right">Powered by Zanovix</TooltipContent>
              </Tooltip>
            </TooltipProvider>
          ) : (
            <span>
              Powered by{" "}
              <span className="font-medium hover:underline">Zanovix</span>
            </span>
          )}
        </a>
      </div>

      {/* User section */}
      <div className="border-t p-2">
        {isCollapsed ? (
          <div className="flex flex-col items-center gap-2">
            <TooltipProvider delayDuration={0}>
              <Tooltip>
                <TooltipTrigger asChild>
                  <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary text-primary-foreground text-sm font-medium cursor-default">
                    {displayName.charAt(0).toUpperCase()}
                  </div>
                </TooltipTrigger>
                <TooltipContent side="right">
                  {displayName} ({roleLabel})
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
            <TooltipProvider delayDuration={0}>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={onLogout}
                    className="h-8 w-8 text-muted-foreground hover:text-foreground"
                  >
                    <LogOut className="h-4 w-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent side="right">Cerrar sesion</TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
        ) : (
          <div className="flex items-center gap-3 rounded-lg bg-sidebar-accent p-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary text-primary-foreground text-sm font-medium flex-shrink-0">
              {displayName.charAt(0).toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-sidebar-foreground truncate">
                {displayName}
              </p>
              <p className="text-xs text-muted-foreground">{roleLabel}</p>
            </div>
            <TooltipProvider delayDuration={0}>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={onLogout}
                    className="h-8 w-8 text-muted-foreground hover:text-foreground flex-shrink-0"
                  >
                    <LogOut className="h-4 w-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent side="top">Cerrar sesion</TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
        )}
      </div>
    </>
  );
}

// ---------------------------------------------------------------------------
// Sidebar — public component
// ---------------------------------------------------------------------------

export function Sidebar() {
  const { logout, user } = useAuth();
  const { isCollapsed, toggle, isMobile, isMobileOpen, setMobileOpen } =
    useSidebar();

  const displayName = user?.display_name || user?.email || "Usuario";
  const roleLabels: Record<string, string> = {
    admin: "Administrador",
    consultor: "Consultor",
    comercial: "Comercial",
  };
  const roleLabel = user?.role ? (roleLabels[user.role] ?? user.role) : "";

  const innerProps = {
    displayName,
    roleLabel,
    onLogout: logout,
  };

  // Mobile: render content inside a Sheet drawer
  if (isMobile) {
    return (
      <Sheet open={isMobileOpen} onOpenChange={setMobileOpen}>
        <SheetContent side="left" className="p-0 flex flex-col w-64">
          <SheetTitle className="sr-only">Menú de navegación</SheetTitle>
          <SidebarInner
            {...innerProps}
            isCollapsed={false}
            onNavClick={() => setMobileOpen(false)}
          />
        </SheetContent>
      </Sheet>
    );
  }

  // Desktop: render inline
  return (
    <div
      className={cn(
        "relative flex h-full flex-col border-r bg-sidebar transition-all duration-300 ease-in-out",
        isCollapsed ? "w-16" : "w-64"
      )}
    >
      {/* Floating Toggle Button */}
      <TooltipProvider delayDuration={0}>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="outline"
              size="icon"
              onClick={toggle}
              className="absolute -right-3 top-20 z-50 h-6 w-6 rounded-full border bg-background shadow-md hover:bg-accent"
            >
              {isCollapsed ? (
                <ChevronRight className="h-3 w-3" />
              ) : (
                <ChevronLeft className="h-3 w-3" />
              )}
            </Button>
          </TooltipTrigger>
          <TooltipContent side="right">
            {isCollapsed ? "Expandir menu" : "Colapsar menu"}
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>

      <SidebarInner {...innerProps} isCollapsed={isCollapsed} />
    </div>
  );
}
