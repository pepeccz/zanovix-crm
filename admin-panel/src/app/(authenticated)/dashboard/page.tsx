"use client";

import { useTranslations } from "next-intl";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PageContainer } from "@/components/shared/page-container";
import { PageHeader } from "@/components/shared/page-header";
import Link from "next/link";
import { UserCheck } from "lucide-react";

export default function DashboardPage() {
  const t = useTranslations();

  return (
    <PageContainer>
      <PageHeader
        title={t("page.dashboard.title")}
        description={t("page.dashboard.lede")}
      />
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Link href="/leads">
          <Card className="hover:bg-accent/50 transition-colors cursor-pointer">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                {t("nav.clients")}
              </CardTitle>
              <UserCheck className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <p className="text-xs text-muted-foreground">
                {t("page.clients.lede")}
              </p>
            </CardContent>
          </Card>
        </Link>
      </div>
    </PageContainer>
  );
}
