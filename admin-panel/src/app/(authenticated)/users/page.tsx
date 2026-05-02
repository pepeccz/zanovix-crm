// TODO Phase 8: restore full users management page
"use client";

import { PageContainer } from "@/components/shared/page-container";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent } from "@/components/ui/card";

export default function UsersPage() {
  return (
    <PageContainer>
      <PageHeader title="Usuarios" description="Gestión de usuarios del sistema" />
      <Card>
        <CardContent className="py-8 text-center text-muted-foreground">
          Gestión de usuarios — próximamente
        </CardContent>
      </Card>
    </PageContainer>
  );
}
