"use server";

import { cookies } from "next/headers";
import { LOCALES, COOKIE_NAME, DEFAULT_LOCALE, type Locale } from "@/i18n/routing";

export async function setLocaleAction(locale: string): Promise<void> {
  const safe: Locale = (LOCALES as readonly string[]).includes(locale)
    ? (locale as Locale)
    : DEFAULT_LOCALE;
  (await cookies()).set(COOKIE_NAME, safe, {
    path: "/",
    maxAge: 60 * 60 * 24 * 365,
    sameSite: "lax",
    httpOnly: false,
    secure: process.env.NODE_ENV === "production",
  });
}
