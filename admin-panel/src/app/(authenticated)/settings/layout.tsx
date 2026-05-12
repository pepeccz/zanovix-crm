"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import { Settings, Server, UserCog } from "lucide-react";
import { useTranslations } from "next-intl";
import { useAuth } from "@/contexts/auth-context";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";

interface TabItem {
  titleKey: "general" | "system" | "admins";
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  adminOnly?: boolean;
}

const tabs: TabItem[] = [
  { titleKey: "general", href: "/settings/config", icon: Settings },
  { titleKey: "system", href: "/settings/system", icon: Server },
  { titleKey: "admins", href: "/settings/admin-users", icon: UserCog, adminOnly: true },
];

export default function SettingsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const { isAdmin } = useAuth();
  const t = useTranslations("page.settings");

  const visibleTabs = tabs.filter((tab) => !tab.adminOnly || isAdmin);

  return (
    <div className="p-6 space-y-6">
      {/* Header compartido */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">{t("layoutTitle")}</h1>
        <p className="text-muted-foreground">{t("layoutSubtitle")}</p>
      </div>

      {/* Navegacion por tabs usando Radix Tabs */}
      <div className="overflow-x-auto">
        <Tabs value={pathname}>
          <TabsList className="w-full sm:w-auto">
            {visibleTabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <TabsTrigger key={tab.href} value={tab.href} asChild>
                  <Link href={tab.href}>
                    <Icon className="h-4 w-4 mr-2" />
                    {t(`tabs.${tab.titleKey}`)}
                  </Link>
                </TabsTrigger>
              );
            })}
          </TabsList>
        </Tabs>
      </div>

      {/* Contenido de las sub-paginas */}
      <div>{children}</div>
    </div>
  );
}
