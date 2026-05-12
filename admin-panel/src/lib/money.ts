/**
 * Money formatting helpers for Zanovix CRM.
 *
 * All values stored as integer cents in the backend.
 * `formatMoney` converts cents to a formatted dollar/euro string.
 */

/**
 * Format an integer cent value as a currency string.
 * Examples:
 *   formatMoney(125000)  → "$1,250"
 *   formatMoney(0)       → "$0"
 *   formatMoney(null)    → "—"
 */
export function formatMoney(cents: number | null | undefined): string {
  if (cents == null) return "—";
  const whole = Math.round(cents / 100);
  return `$${whole.toLocaleString("en-US")}`;
}

/**
 * Format as a monthly rate (append "/mo").
 * Examples:
 *   formatMonthly(125000) → "$1,250/mo"
 */
export function formatMonthly(cents: number | null | undefined): string {
  if (cents == null) return "—";
  return `${formatMoney(cents)}/mo`;
}
