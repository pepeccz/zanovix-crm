import { NextIntlClientProvider } from "next-intl";
import { getLocale, getMessages } from "next-intl/server";
import { BrandProvider } from "@/contexts/brand-context";
import { AppShell } from "@/components/layout/app-shell";
import { AppBreadcrumb } from "@/components/layout/app-breadcrumb";
import { AuthGate } from "./_components/auth-gate";

export default async function AuthenticatedLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const locale = await getLocale();
  const messages = await getMessages();

  return (
    <NextIntlClientProvider locale={locale} messages={messages}>
      <BrandProvider>
        <AuthGate>
          <AppShell>
            <AppBreadcrumb />
            {children}
          </AppShell>
        </AuthGate>
      </BrandProvider>
    </NextIntlClientProvider>
  );
}
