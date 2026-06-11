/**
 * Date parsing and formatting utility — no business logic.
 * Uses date-fns for formatting with standard pattern tokens.
 *
 * Pattern tokens (date-fns):
 *   yyyy, yy       — year
 *   MMMM, MMM, MM, M — month
 *   dd, d          — day of month
 *   HH, H          — hour 24h
 *   hh, h          — hour 12h
 *   mm, m          — minutes
 *   ss, s          — seconds
 *   aaa, a         — am/pm
 *   Literal text in single quotes: 'at', ':'
 *
 * Example: formatDate("2026-03-29T22:05:00Z", "MMM d h:mm aaa")
 *          → "Mar 29 10:05 pm"
 */

import { format as formatDateFns } from "date-fns";

/**
 * Parse a raw date string into a Date object.
 * Returns null if the input can't be parsed.
 */
export function parseDate(raw: string): Date | null {
    const d = new Date(raw);
    return Number.isNaN(d.getTime()) ? null : d;
}

/**
 * Format a date string or Date using a date-fns pattern.
 * Returns the raw input string if it can't be parsed.
 */
export function formatDate(raw: string | Date, pattern: string): string {
    const d = raw instanceof Date ? raw : parseDate(String(raw));
    if (!d) return String(raw);
    return formatDateFns(d, pattern);
}

/**
 * Convert a Date or unix timestamp (seconds) to ISO 8601 string.
 */
export function toISOString(input: Date | number): string {
    const d = typeof input === "number" ? new Date(input * 1000) : input;
    return d.toISOString();
}

/**
 * Get the current time as an ISO 8601 string.
 */
export function nowISO(): string {
    return new Date().toISOString();
}
