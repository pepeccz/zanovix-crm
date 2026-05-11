import type { Metadata } from "next";
import { Inter, Newsreader, League_Spartan, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { getLocale } from "next-intl/server";
import { AuthProvider } from "@/contexts/auth-context";
import { SidebarProvider } from "@/contexts/sidebar-context";
import { SileoToaster } from "@/components/sileo-toaster";
import { THEME_INIT_SCRIPT } from "./theme-init";

const inter = Inter({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-inter",
  display: "swap",
});

const newsreader = Newsreader({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600"],
  style: ["normal", "italic"],
  variable: "--font-newsreader",
  display: "swap",
});

const leagueSpartan = League_Spartan({
  subsets: ["latin"],
  weight: ["700", "900"],
  variable: "--font-league-spartan",
  display: "swap",
});

const jetbrains = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400"],
  variable: "--font-jetbrains-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Zanovix CRM",
  description: "Panel de gestión de leads y oportunidades",
  icons: {
    icon: "/logo-isotipo.png",
    apple: "/logo-isotipo.png",
  },
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const locale = await getLocale();
  return (
    <html lang={locale} suppressHydrationWarning className={`${inter.variable} ${newsreader.variable} ${leagueSpartan.variable} ${jetbrains.variable}`}>
      <head>
        {/* FOUC prevention: apply theme before first paint */}
        {/* Hash pinned in next.config.ts — see src/__tests__/csp-hash.test.ts for drift detection */}
        <script
          dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }}
        />
      </head>
      <body className="font-sans antialiased">
        <AuthProvider>
          <SidebarProvider>{children}</SidebarProvider>
        </AuthProvider>
        <SileoToaster />
      </body>
    </html>
  );
}
