"use client";

import { PageContainer } from "@/components/shared/page-container";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent } from "@/components/ui/card";

export default function AdminUsersPage() {
  return (
    <PageContainer>
      <PageHeader title="Usuarios" description="Gestión de usuarios del panel" />
      <Card>
        <CardContent className="py-8 text-center text-muted-foreground">
          Gestión de usuarios — próximamente
        </CardContent>
      </Card>
    </PageContainer>
  );
}
