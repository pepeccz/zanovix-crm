"use client";

import { useTranslations } from "next-intl";
import { ReceiptText } from "lucide-react";

export default function BillingPage() {
  const t = useTranslations();

  return (
    <div className="-m-10">
      <header className="border-b border-zx-rule px-10 py-8">
        <p className="font-serif italic text-[14px] text-zx-green mb-2">
          — {t("page.client.billing.eyebrow")}
        </p>
        <h1 className="font-serif text-5xl font-light tracking-tight text-zx-ink leading-tight max-w-3xl">
          {t("page.client.billing.title")}
        </h1>
      </header>
      <div className="flex flex-col items-center justify-center gap-4 py-24 text-center">
        <ReceiptText className="h-12 w-12 text-zx-ink-mute" />
        <p className="font-serif italic text-xl text-zx-ink-mute">
          {t("page.client.billing.comingSoon")}
        </p>
      </div>
    </div>
  );
}
