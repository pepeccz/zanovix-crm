// TODO Phase 8: restore full users management page
"use client";

import { useTranslations } from "next-intl";
import { PageContainer } from "@/components/shared/page-container";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent } from "@/components/ui/card";

export default function UsersPage() {
  const t = useTranslations("page.users");

  return (
    <PageContainer>
      <PageHeader
        title={t("title")}
        description={t("lede")}
      />
      <Card>
        <CardContent className="py-8 text-center text-muted-foreground">
          {t("comingSoon")}
        </CardContent>
      </Card>
    </PageContainer>
  );
}
