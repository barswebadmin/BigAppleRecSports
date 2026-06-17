/** Shopify store identity + every URL that derives from it. */

import { envOr } from "./env.ts";

/** One source of truth for the Shopify store; every store URL/domain derives from it. */
export const STORE = {
    id: envOr("SHOPIFY_STORE_ID", "09fe59-3"),
    api_version: envOr("SHOPIFY_API_VERSION", "2025-01"),
};

export const STORE_MYSHOPIFY_DOMAIN = `${STORE.id}.myshopify.com`;

/** Organization domain (no scheme/subdomain). Website + email addresses derive from it. */
export const ORG_DOMAIN = envOr("ORG_DOMAIN", "bigapplerecsports.com");

export const BARS_URLS = {
    website: envOr("BARS_WEBSITE_URL", `https://www.${ORG_DOMAIN}`),
    admin_ui: `https://admin.shopify.com/store/${STORE.id}`,
    admin_api: `https://${STORE.id}/admin/api/${STORE.api_version}/graphql.json`,
};

/** Google API endpoints. Their hosts are mirrored in `OUTGOING_DOMAINS` for the manifest. */
export const GOOGLE_API = {
    oauth_token_url: "https://oauth2.googleapis.com/token",
    sheets_base: "https://sheets.googleapis.com/v4/spreadsheets",
    gmail_base: "https://gmail.googleapis.com/gmail/v1",
    scopes: [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://mail.google.com/",
    ],
};

/** Shopify admin customer page from a customer GID (`gid://shopify/Customer/<n>`) or numeric id. */
export function shopifyCustomerAdminUrl(idOrGid: string | number): string {
    const numeric = String(idOrGid).split("/").pop();
    return `${BARS_URLS.admin_ui}/customers/${numeric}`;
}

/** Storefront product page from a product handle. */
export function productPageUrl(handle: string): string {
    return `${BARS_URLS.website}/products/${handle}`;
}
