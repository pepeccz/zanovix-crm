// TODO Phase 8: restore full user detail page
"use client";

import { PageContainer } from "@/components/shared/page-container";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent } from "@/components/ui/card";

export default function UserDetailPage() {
  return (
    <PageContainer>
      <PageHeader title="Detalle de usuario" />
      <Card>
        <CardContent className="py-8 text-center text-muted-foreground">
          Detalle de usuario — próximamente
        </CardContent>
      </Card>
    </PageContainer>
  );
}
