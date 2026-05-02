/**
 * Security headers builder — shared between next.config.ts and jest tests.
 *
 * Exported separately so jest (CommonJS) can import it without having to
 * parse the full next.config.ts ESM module.
 *
 * NOTE: script-src uses 'unsafe-inline' WITHOUT a hash on purpose.
 *
 * Per CSP3 §6.7.2, when a hash- or nonce-source is present in script-src,
 * 'unsafe-inline' is IGNORED. Next.js production runtime emits 5–6 inline
 * scripts (hydration bootstrap, RSC payload, font preload optimisation,
 * error boundary stub, theme-init) whose hashes change per build. Listing a
 * single hash blocks all the others and breaks the entire app.
 *
 * For an internal admin panel served over an SSH tunnel with no external
 * surface, 'unsafe-inline' is the operationally correct choice. Promote to
 * a nonce-based CSP via Next proxy/middleware (forces dynamic rendering)
 * before exposing this panel publicly.
 */
import * as crypto from "crypto";
import { THEME_INIT_SCRIPT } from "./theme-init";

export interface HeaderEntry {
  key: string;
  value: string;
}

/**
 * Compute the CSP-formatted sha256 hash of THEME_INIT_SCRIPT.
 * Kept available for future nonce/hash migration; not currently used in CSP.
 */
export function computeThemeScriptHash(): string {
  const base64 = crypto
    .createHash("sha256")
    .update(THEME_INIT_SCRIPT)
    .digest("base64");
  return `'sha256-${base64}'`;
}

/**
 * Return the array of security headers to be used in next.config.ts headers().
 * This function is pure and synchronous — safe to call from both Next.js and jest.
 */
export function buildSecurityHeaders(): HeaderEntry[] {
  const csp = [
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob: https:",
    "connect-src 'self'",
    "font-src 'self' data:",
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
  ].join("; ");

  return [
    {
      key: "Content-Security-Policy",
      value: csp,
    },
    {
      key: "X-Frame-Options",
      value: "DENY",
    },
    {
      key: "X-Content-Type-Options",
      value: "nosniff",
    },
    {
      key: "Referrer-Policy",
      value: "strict-origin-when-cross-origin",
    },
    {
      key: "Permissions-Policy",
      value: "camera=(), microphone=(), geolocation=(), payment=()",
    },
  ];
}
