import { getRequestConfig } from "next-intl/server";
import { cookies } from "next/headers";
import { COOKIE_NAME, DEFAULT_LOCALE, LOCALES, type Locale } from "./routing";

export default getRequestConfig(async () => {
  const store = await cookies();
  const raw = store.get(COOKIE_NAME)?.value;
  const locale: Locale = (LOCALES as readonly string[]).includes(raw ?? "")
    ? (raw as Locale)
    : DEFAULT_LOCALE;
  const messages = (await import(`../../messages/${locale}.json`)).default;
  return { locale, messages };
});
