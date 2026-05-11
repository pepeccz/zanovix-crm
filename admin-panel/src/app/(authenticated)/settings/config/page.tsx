// TODO Phase 8: restore full config page when backend settings endpoint is implemented
"use client";

import { useTranslations } from "next-intl";
import { PageContainer } from "@/components/shared/page-container";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent } from "@/components/ui/card";

export default function ConfigPage() {
  const t = useTranslations("page.settings");

  return (
    <PageContainer>
      <PageHeader title={t("title")} description={t("subtitle")} />
      <Card>
        <CardContent className="py-8 text-center text-muted-foreground">
          Configuración del sistema — próximamente
        </CardContent>
      </Card>
    </PageContainer>
  );
}
