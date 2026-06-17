/**
 * PreparedRequest — a fully-formed HTTP request that has NOT yet been sent.
 *
 * Every network call in this app is split into a builder (produces a
 * PreparedRequest, doing only the read/auth lookups needed to make the bytes
 * exact) and an executor (sends it). Dry-run mode runs only the builders and
 * renders the result, so what it shows is byte-for-byte what prod would send.
 */

export interface PreparedRequest {
    /** Human label for the operation, e.g. "Shopify customerUpdate — add tag". */
    label: string;
    method: string;
    url: string;
    headers: Record<string, string>;
    /** Serialized body exactly as it will be sent (undefined for GET). */
    body?: string;
    /**
     * Optional human-readable rendering of the body for dry-run display only
     * (e.g. a decoded email instead of a 150KB base64 blob). Never sent — the
     * executor always uses `body`.
     */
    displayBody?: string;
}

const SENSITIVE_HEADERS = new Set(["authorization", "x-shopify-access-token"]);

/** Mask a credential as `abc...xyz`, hiding everything but the first/last 3 chars. */
export function maskSecret(value: string): string {
    if (value.length <= 6) return "***";
    return `${value.slice(0, 3)}...${value.slice(-3)}`;
}

/**
 * Return a copy of headers with credential values masked. Preserves an auth
 * scheme prefix (e.g. `Bearer `) and masks only the token after it.
 */
export function maskHeaders(headers: Record<string, string>): Record<string, string> {
    const out: Record<string, string> = {};
    for (const [key, value] of Object.entries(headers)) {
        if (!SENSITIVE_HEADERS.has(key.toLowerCase())) {
            out[key] = value;
            continue;
        }
        const scheme = value.match(/^(\S+\s+)(.+)$/);
        out[key] = scheme ? `${scheme[1]}${maskSecret(scheme[2])}` : maskSecret(value);
    }
    return out;
}
