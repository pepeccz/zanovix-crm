"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChevronRight, Home } from "lucide-react";
import { useTranslations } from "next-intl";

function isUUID(segment: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(
    segment
  );
}

export function AppBreadcrumb() {
  const pathname = usePathname();
  const tNav = useTranslations("nav");
  const tSettings = useTranslations("page.settings");
  const tBreadcrumb = useTranslations("breadcrumb");

  // Mapping segments -> translation lookups
  function getSegmentLabel(segment: string): string {
    if (isUUID(segment)) {
      // Generic detail label — could be expanded per-section if needed
      return segment.slice(0, 8);
    }
    // nav.* covers top-level routes
    const navKeys = [
      "dashboard",
      "pipeline",
      "clients",
      "leads",
      "services",
      "billing",
      "calendar",
      "team",
      "users",
      "settings",
      "projects",
      "documents",
      "meetings",
      "support",
      "chat",
    ];
    if (navKeys.includes(segment)) {
      return tNav(segment);
    }
    // settings sub-tabs
    if (segment === "config") return tSettings("tabs.general");
    if (segment === "system") return tSettings("tabs.system");
    if (segment === "admin-users") return tSettings("tabs.admins");
    // Fallback: capitalise
    return segment.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  }

  // Filtrar segmentos vacíos y grupos de rutas Next.js como (authenticated)
  const segments = pathname
    .split("/")
    .filter(Boolean)
    .filter((s) => !s.startsWith("("));

  // No mostrar en la raíz ni en páginas de primer nivel (ej: /dashboard solo)
  if (segments.length <= 1) return null;

  const crumbs = segments.map((segment, idx) => {
    const href = "/" + segments.slice(0, idx + 1).join("/");
    const label = getSegmentLabel(segment);
    const isLast = idx === segments.length - 1;
    return { href, label, isLast };
  });

  return (
    <nav
      aria-label="Breadcrumb"
      className="flex items-center gap-1 px-6 py-2 text-sm border-b bg-background text-muted-foreground"
    >
      <Link
        href="/dashboard"
        className="hover:text-foreground transition-colors flex items-center"
        aria-label={tBreadcrumb("home")}
      >
        <Home className="h-3.5 w-3.5" />
      </Link>
      {crumbs.map((crumb) => (
        <span key={crumb.href} className="flex items-center gap-1">
          <ChevronRight className="h-3.5 w-3.5 flex-shrink-0" />
          {crumb.isLast ? (
            <span className="text-foreground font-medium">{crumb.label}</span>
          ) : (
            <Link
              href={crumb.href}
              className="hover:text-foreground transition-colors"
            >
              {crumb.label}
            </Link>
          )}
        </span>
      ))}
    </nav>
  );
}
