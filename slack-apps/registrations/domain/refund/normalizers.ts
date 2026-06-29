/**
 * Refund-domain normalizers. Pure functions that map raw inputs (sheet cell
 * strings, etc.) to canonical refund-domain values. No HTTP, no I/O.
 */

import type { RefundTo } from "./types.ts";

const warn = (fn: string, ...args: unknown[]) =>
  console.warn(`[refund_normalizers:${fn}]`, ...args);

/**
 * Normalize a raw `refundOrCredit` cell value to the canonical `RefundTo`.
 *
 *   - Any value containing "credit" (case-insensitive) → `"store_credit"`.
 *   - Anything else (including the typical "refund to original form of payment"
 *     answer) → `"original_method"`.
 *   - `null` / empty raw → `"original_method"`, with a warning log so drift
 *     (renamed answer choices) is visible.
 */
export function normalizeRefundOrCredit(
  raw: string | null | undefined,
): RefundTo {
  if (raw === null || raw === undefined || raw.trim() === "") {
    warn(
      "normalizeRefundOrCredit",
      "raw value is null/empty; defaulting to original_method",
    );
    return "original_method";
  }
  return raw.toLowerCase().includes("credit")
    ? "store_credit"
    : "original_method";
}
