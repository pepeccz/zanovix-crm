// TODO Phase 8: restore system monitor when backend endpoints are implemented
"use client";

import { PageContainer } from "@/components/shared/page-container";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent } from "@/components/ui/card";

export default function SystemPage() {
  return (
    <PageContainer>
      <PageHeader title="Sistema" description="Estado del sistema" />
      <Card>
        <CardContent className="py-8 text-center text-muted-foreground">
          Monitor del sistema — próximamente
        </CardContent>
      </Card>
    </PageContainer>
  );
}
