"use client";

import { useState } from "react";
import Image from "next/image";
import { useTranslations } from "next-intl";
import { useAuth } from "@/contexts/auth-context";
import { LocaleToggle } from "@/components/layout/locale-toggle";
import { sileo } from "sileo";
import { Loader2 } from "lucide-react";

type Role = "team" | "client";

export default function LoginPage() {
  const t = useTranslations("page.login");
  const [role, setRole] = useState<Role>("team");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(true);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const { login } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);
    try {
      await login(email, password);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error");
    } finally {
      setIsLoading(false);
    }
  };

  const comingSoon = () => sileo.info({ title: t("comingSoon") });

  return (
    <div className="grid min-h-screen grid-cols-1 lg:grid-cols-2">
      {/* LEFT — editorial dark panel */}
      <aside className="relative hidden flex-col justify-between bg-zx-night px-12 py-10 text-zx-paper lg:flex">
        <header className="flex items-center gap-3">
          <Image
            src="/brand/zanovix-flower.png"
            alt="Zanovix"
            width={36}
            height={36}
            priority
            className="opacity-90"
          />
          <span className="font-sans text-[13px] font-semibold uppercase tracking-[0.32em] text-zx-paper">
            Zanovix
          </span>
        </header>

        <div className="max-w-xl">
          <p className="mb-6 font-sans text-[11px] font-semibold uppercase tracking-[0.18em] text-zx-green-light">
            — {t("eyebrowLeft")}
          </p>
          <h1 className="font-serif text-5xl font-light leading-[1.05] tracking-[-0.02em] text-zx-paper xl:text-[56px]">
            {t("headlinePre")}{" "}
            <em className="font-serif italic text-zx-green-light">
              {t("headlineEm")}
            </em>
            {t("headlinePost")}
          </h1>
          <p className="mt-8 max-w-lg font-serif text-[17px] italic leading-[1.55] text-zx-paper/60">
            {t("lede")}
          </p>
        </div>

        <footer className="flex items-center justify-between font-sans text-[11px] uppercase tracking-[0.18em] text-zx-paper/45">
          <span>{t("footerLocation")}</span>
          <span>{t("footerSecure")}</span>
        </footer>
      </aside>

      {/* RIGHT — form panel */}
      <section className="relative flex flex-col justify-center bg-zx-paper px-6 py-10 sm:px-12 lg:px-16">
        <div className="absolute right-6 top-6 sm:right-12 sm:top-10">
          <LocaleToggle />
        </div>

        <div className="mx-auto w-full max-w-md">
          <p className="font-sans text-[11px] font-semibold uppercase tracking-[0.18em] text-zx-green">
            — {t("eyebrowRight")}
          </p>
          <h2 className="mt-3 font-serif text-[44px] font-light leading-[1.05] tracking-[-0.02em] text-zx-ink">
            {t("title")}
          </h2>
          <p className="mt-3 font-serif text-[17px] italic leading-[1.55] text-zx-ink/55">
            {t("subtitle")}
          </p>

          {/* Role tabs */}
          <div className="mt-8 grid grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => setRole("team")}
              className={
                "flex flex-col items-start rounded-[2px] border px-4 py-3 text-left transition-colors " +
                (role === "team"
                  ? "border-zx-ink bg-zx-ink text-zx-paper"
                  : "border-zx-rule bg-transparent text-zx-ink hover:bg-zx-paper-2")
              }
              aria-pressed={role === "team"}
            >
              <span className="font-sans text-[13px] font-semibold">
                {t("roleTeam")}
              </span>
              <span
                className={
                  "mt-0.5 font-sans text-[11px] " +
                  (role === "team" ? "text-zx-paper/60" : "text-zx-ink-mute")
                }
              >
                {t("roleTeamSub")}
              </span>
            </button>
            <button
              type="button"
              onClick={() => setRole("client")}
              className={
                "flex flex-col items-start rounded-[2px] border px-4 py-3 text-left transition-colors " +
                (role === "client"
                  ? "border-zx-ink bg-zx-ink text-zx-paper"
                  : "border-zx-rule bg-transparent text-zx-ink hover:bg-zx-paper-2")
              }
              aria-pressed={role === "client"}
            >
              <span className="font-sans text-[13px] font-semibold">
                {t("roleClient")}
              </span>
              <span
                className={
                  "mt-0.5 font-sans text-[11px] " +
                  (role === "client" ? "text-zx-paper/60" : "text-zx-ink-mute")
                }
              >
                {t("roleClientSub")}
              </span>
            </button>
          </div>

          <form onSubmit={handleSubmit} className="mt-6 space-y-5">
            {error && (
              <div className="rounded-[2px] border border-[#cc3c28]/30 bg-[#cc3c28]/5 px-3 py-2 font-sans text-[12px] text-[#cc3c28]">
                {error}
              </div>
            )}

            <div className="space-y-1.5">
              <label
                htmlFor="email"
                className="font-sans text-[11px] font-semibold uppercase tracking-[0.18em] text-zx-ink-mute"
              >
                {t("email")}
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder={t("emailPlaceholder")}
                autoComplete="email"
                required
                disabled={isLoading}
                className="block w-full rounded-[2px] border border-zx-rule bg-transparent px-3 py-2.5 font-sans text-[14px] text-zx-ink placeholder:text-zx-ink-mute focus:border-zx-green focus:outline-none focus:ring-1 focus:ring-zx-green/30"
              />
            </div>

            <div className="space-y-1.5">
              <div className="flex items-baseline justify-between">
                <label
                  htmlFor="password"
                  className="font-sans text-[11px] font-semibold uppercase tracking-[0.18em] text-zx-ink-mute"
                >
                  {t("password")}
                </label>
                <button
                  type="button"
                  onClick={comingSoon}
                  className="font-sans text-[12px] text-zx-green underline-offset-2 hover:underline"
                >
                  {t("forgot")}
                </button>
              </div>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••"
                autoComplete="current-password"
                required
                disabled={isLoading}
                className="block w-full rounded-[2px] border border-zx-rule bg-transparent px-3 py-2.5 font-sans text-[14px] text-zx-ink placeholder:text-zx-ink-mute focus:border-zx-green focus:outline-none focus:ring-1 focus:ring-zx-green/30"
              />
            </div>

            <label className="flex items-center gap-2 font-sans text-[13px] text-zx-ink-soft">
              <input
                type="checkbox"
                checked={remember}
                onChange={(e) => setRemember(e.target.checked)}
                className="h-4 w-4 rounded-[2px] border border-zx-rule text-zx-green accent-zx-green focus:ring-zx-green/40"
              />
              {t("remember")}
            </label>

            <button
              type="submit"
              disabled={isLoading}
              className="flex w-full items-center justify-center gap-2 rounded-[2px] bg-zx-green px-4 py-3 font-sans text-[14px] font-semibold text-zx-paper transition-colors hover:bg-zx-green-dark disabled:opacity-60"
            >
              {isLoading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  {t("loading")}
                </>
              ) : (
                <>
                  {t("submit")} <span aria-hidden>→</span>
                </>
              )}
            </button>

            <div className="flex items-center gap-3">
              <div className="h-px flex-1 bg-zx-rule" />
              <span className="font-sans text-[11px] uppercase tracking-[0.18em] text-zx-ink-mute">
                {t("divider")}
              </span>
              <div className="h-px flex-1 bg-zx-rule" />
            </div>

            <button
              type="button"
              onClick={comingSoon}
              className="flex w-full items-center justify-center gap-3 rounded-[2px] border border-zx-rule bg-transparent px-4 py-2.5 font-sans text-[13px] text-zx-ink transition-colors hover:bg-zx-paper-2"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden>
                <path
                  fill="#4285F4"
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.76h3.56c2.08-1.92 3.28-4.74 3.28-8.09Z"
                />
                <path
                  fill="#34A853"
                  d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.56-2.76c-.99.66-2.25 1.06-3.72 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84A11 11 0 0 0 12 23Z"
                />
                <path
                  fill="#FBBC05"
                  d="M5.84 14.11A6.6 6.6 0 0 1 5.48 12c0-.73.13-1.45.36-2.11V7.05H2.18A11 11 0 0 0 1 12c0 1.78.43 3.46 1.18 4.95l3.66-2.84Z"
                />
                <path
                  fill="#EA4335"
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.05l3.66 2.84C6.71 7.31 9.14 5.38 12 5.38Z"
                />
              </svg>
              {t("google")}
            </button>
          </form>

          <footer className="mt-8 flex items-center justify-between font-sans text-[12px] text-zx-ink-mute">
            <span>{t("footer")}</span>
            <button
              type="button"
              onClick={comingSoon}
              className="underline-offset-2 hover:underline"
            >
              {t("privacy")}
            </button>
          </footer>
        </div>
      </section>
    </div>
  );
}
