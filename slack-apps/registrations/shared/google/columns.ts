/**
 * Generic Google-sheet column-header helper. Domain-agnostic — every workflow
 * that reads a sheet whose header row may shift over time (Google Forms add
 * questions, sheets get edited) routes column lookups through this helper
 * rather than hard-coding column letters.
 */

/**
 * Case-insensitive substring match against the header row. Returns the
 * 0-based column index, or `null` when no header contains the substring.
 *
 * The matcher is intentionally permissive (substring, not equality) so a
 * canonical short token (e.g. `"order number"`) can match a long, free-form
 * Google-Form question header (e.g. `"Please provide the Order Number you're
 * requesting a refund for…"`).
 */
export function findColumn(
    headers: string[],
    substring: string,
): number | null {
    const target = substring.toLowerCase();
    const idx = headers.findIndex((h) => h.toLowerCase().includes(target));
    return idx === -1 ? null : idx;
}
