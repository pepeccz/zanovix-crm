/**
 * Security headers builder — shared between next.config.ts and jest tests.
 *
 * Exported separately so jest (CommonJS) can import it without having to
 * parse the full next.config.ts ESM module.
 *
 * NOTE: script-src uses 'unsafe-inline' to accommodate Next.js production
 * runtime (hydration bootstrap, __NEXT_DATA__, chunk loading). A nonce-based
 * CSP via Next middleware is the proper long-term fix; tracked as TODO for
 * production hardening. For now this matches the operational reality of an
 * internal-only admin panel served over an SSH tunnel.
 */
import * as crypto from "crypto";
import { THEME_INIT_SCRIPT } from "./theme-init";

export interface HeaderEntry {
  key: string;
  value: string;
}

/**
 * Compute the CSP-formatted sha256 hash of THEME_INIT_SCRIPT.
 * Format: 'sha256-<base64>'
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
  const themeHash = computeThemeScriptHash();

  const csp = [
    "default-src 'self'",
    `script-src 'self' 'unsafe-inline' 'unsafe-eval' ${themeHash}`,
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
