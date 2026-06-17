/** Environment / deployment switches. The single inputs that flip routing. */

export type Env = "test" | "prod";

/** Read an env var, tolerating runtimes where env access is unavailable. */
export function readEnv(key: string): string | undefined {
    try {
        return Deno.env.get(key) ?? undefined;
    } catch {
        return undefined;
    }
}

export function envOr(key: string, fallback: string): string {
    return readEnv(key) ?? fallback;
}

/**
 * The single deployment switch. `ENV=prod` routes refund reviews to the live
 * channel and lets the irreversible Shopify calls fire; any other value
 * (default) keeps the app test-only.
 */
export const ENV: Env = readEnv("ENV") === "prod" ? "prod" : "test";
