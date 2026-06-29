/** Environment helpers + store identity + every URL that derives from it. */

// ── Environment helpers ───────────────────────────────────────────────────────

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
export type Env = "test" | "prod";
export const ENV: Env = readEnv("ENV") === "prod" ? "prod" : "test";

// ── Store identity ────────────────────────────────────────────────────────────

/** One source of truth for the Shopify store; every store URL/domain derives from it. */
const STORE = {
  id: envOr("SHOPIFY__STORE_ID", "09fe59-3"),
  api_version: envOr("SHOPIFY__API_VERSION", "2026-07"),
};

export const STORE_MYSHOPIFY_DOMAIN = `${STORE.id}.myshopify.com`;

/** Organization domain (no scheme/subdomain). Website + email addresses derive from it. */
export const ORG_DOMAIN = envOr("ORG_DOMAIN", "bigapplerecsports.com");

export const BARS_URLS = {
  website: envOr("BARS_WEBSITE_URL", `https://www.${ORG_DOMAIN}`),
  admin_ui: `https://admin.shopify.com/store/${STORE.id}`,
  admin_api: `https://${STORE.id}/admin/api/${STORE.api_version}/graphql.json`,
};

/** Google API endpoints. Canonical source: lib/external_apis.py */
export const GOOGLE_API = {
  oauth_token_url: "https://oauth2.googleapis.com/token",
  sheets_base: "https://sheets.googleapis.com/v4/spreadsheets",
  gmail_base: "https://gmail.googleapis.com/gmail/v1",
  scopes: [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://mail.google.com/",
  ],
} as const;

/** Shopify admin customer page from a customer GID (`gid://shopify/Customer/<n>`) or numeric id. */
export function shopifyCustomerAdminUrl(idOrGid: string | number): string {
  const numeric = String(idOrGid).split("/").pop();
  return `${BARS_URLS.admin_ui}/customers/${numeric}`;
}

/** Storefront product page from a product handle. */
export function productPageUrl(handle: string): string {
  return `${BARS_URLS.website}/products/${handle}`;
}

// ── BARS API endpoint ────────────────────────────────────────────────────────

/** Canonical BARS HTTP API base (e.g. `https://api.bigapplerecsports.com`). No trailing slash.
 *  Refund approvals POST to `{base}/refunds/create` and DELETE `{base}/orders/{id}`. */
export function barsApiBaseUrl(): string | undefined {
  const raw = readEnv("BARS_API_URL")?.trim();
  return raw ? raw.replace(/\/+$/, "") : undefined;
}

export function barsApiDomain(): string | undefined {
  const base = barsApiBaseUrl();
  if (!base) return undefined;
  try {
    return new URL(base).host;
  } catch {
    return undefined;
  }
}

/** Comma-separated Slack user IDs allowed to exceed the soft refund estimate without exec routing. */
export function isRefundPrivilegedSlackUser(userId: string): boolean {
  const raw = readEnv("REFUND_PRIVILEGED_SLACK_USER_IDS");
  if (!raw?.trim()) return false;
  const ids = raw
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
  return ids.includes(userId);
}
