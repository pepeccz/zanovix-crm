import { NextIntlClientProvider } from "next-intl";
import { getLocale, getMessages } from "next-intl/server";
import { BrandProvider } from "@/contexts/brand-context";
import { ClientAppShell } from "@/components/layout/client-portal/client-app-shell";
import { ClientAuthGate } from "./_components/client-auth-gate";

export default async function ClientPortalLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const locale = await getLocale();
  const messages = await getMessages();

  return (
    <NextIntlClientProvider locale={locale} messages={messages}>
      <BrandProvider>
        <ClientAuthGate>
          <ClientAppShell>{children}</ClientAppShell>
        </ClientAuthGate>
      </BrandProvider>
    </NextIntlClientProvider>
  );
}
