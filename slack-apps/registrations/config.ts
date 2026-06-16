// ── Season ──────────────────────────────────────────────────────────

import { buildLeagueKey } from "./lib/waitlists/league_key.ts";

export const CURRENT_YEAR = 2026;
export const CURRENT_SEASON = "summer";

export type Season = "winter" | "spring" | "summer" | "fall";
export const ALL_SEASONS: Season[] = ["winter", "spring", "summer", "fall"];

// ── Environment ─────────────────────────────────────────────────────

export type Env = "test" | "prod";

/** Read an env var, tolerating runtimes where env access is unavailable. */
function readEnv(key: string): string | undefined {
    try {
        return Deno.env.get(key) ?? undefined;
    } catch {
        return undefined;
    }
}

function envOr(key: string, fallback: string): string {
    return readEnv(key) ?? fallback;
}

/**
 * The single deployment switch. `ENV=prod` routes refund reviews to the live
 * channel and lets the irreversible Shopify calls fire; any other value
 * (default) keeps the app test-only. This is the one input that flips routing.
 */
export const ENV: Env = readEnv("ENV") === "prod" ? "prod" : "test";

// ── Store identity ──────────────────────────────────────────────────

/** One source of truth for the Shopify store; every store URL/domain derives from it. */
export const STORE = {
    id: envOr("SHOPIFY_STORE_ID", "09fe59-3"),
    api_version: envOr("SHOPIFY_API_VERSION", "2025-01"),
};

export const STORE_MYSHOPIFY_DOMAIN = `${STORE.id}.myshopify.com`;

// ── URLs ────────────────────────────────────────────────────────────

/** Organization domain (no scheme/subdomain). Website + email addresses derive from it. */
export const ORG_DOMAIN = envOr("ORG_DOMAIN", "bigapplerecsports.com");

export const BARS_URLS = {
    website: envOr("BARS_WEBSITE_URL", `https://www.${ORG_DOMAIN}`),
    admin_ui: `https://admin.shopify.com/store/${STORE.id}`,
    admin_api: `https://${STORE.id}/admin/api/${STORE.api_version}/graphql.json`,
};

/** Google API endpoints. Their hosts are mirrored in OUTGOING_DOMAINS for the manifest. */
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

// ── Slack UI helpers ────────────────────────────────────────────────

/**
 * Default hyperlink display text reused across workflows. Keep link copy here
 * so it stays consistent everywhere (and the emoji is changed in one place).
 */
export const SLACK_LINK_TEXT = {
    googleSheets: ":paperclip: Open in Google Sheets",
    shopifyCustomer: "Shopify profile",
    productPage: "product page",
} as const;

/** Slack mrkdwn hyperlink: `<url|text>`. */
export function slackLink(text: string, url: string): string {
    return `<${url}|${text}>`;
}

/** Mention a Slack member with a leading label, e.g. `Processed by <@U123>`. */
export function tagSlackMember(userId: string, prefix = "Processed by"): string {
    return `${prefix} <@${userId}>`;
}

/** Weekday ordering for league sorting (Mon first … Sun last), not alphabetical. */
export const WEEKDAY_ORDER = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
];

export function compareWeekday(a: string, b: string): number {
    return WEEKDAY_ORDER.indexOf(a.toLowerCase()) - WEEKDAY_ORDER.indexOf(b.toLowerCase());
}

// ── Gmail ───────────────────────────────────────────────────────────

export const DEFAULT_GMAIL_SENDER = {
    name: "Big Apple Rec Sports",
    email_address: `web@${ORG_DOMAIN}`,
};

// ── Refunds ─────────────────────────────────────────────────────────

export const REFUND_TEST_CHANNEL = envOr("REFUND_TEST_CHANNEL", "#joe-test");
export const REFUND_REVIEW_CHANNEL = envOr("REFUND_REVIEW_CHANNEL", "#exec-leadership-2026");

// ShopifyRefundHandler Lambda Function URL — receives the approve/process POST
// when a reviewer confirms a refund. Auth is NONE, so treat the URL as
// semi-secret. Its host (derived below) must be in OUTGOING_DOMAINS.
export const REFUND_PROCESS_URL = envOr(
    "REFUND_PROCESS_URL",
    "https://7wfkjr4jk5hbchf23venzdm3te0yaouc.lambda-url.us-east-1.on.aws/",
);
export const REFUND_PROCESS_DOMAIN = new URL(REFUND_PROCESS_URL).host;

// In non-prod, approving a refund POSTs the cancel/refund payloads to the test
// channel as a preview instead of hitting the Lambda — letting us validate the
// irreversible Shopify calls before they fire. `ENV=prod` (or an explicit
// `REFUND_DRY_RUN` override) sends them for real.
export const REFUND_DRY_RUN = (readEnv("REFUND_DRY_RUN") ?? String(ENV !== "prod")) === "true";

/**
 * Route a refund review message. In test mode everything stays in the test
 * channel; in prod only requests explicitly flagged `is_test` divert there.
 */
export function resolveRefundChannel(opts: { is_test?: boolean }): string {
    const useTest = ENV === "test" || opts.is_test === true;
    return useTest ? REFUND_TEST_CHANNEL : REFUND_REVIEW_CHANNEL;
}

// ── Manifest allowlist ──────────────────────────────────────────────

/** Every external host the app calls. Single source for `manifest.outgoingDomains`. */
export const OUTGOING_DOMAINS = [
    "www.googleapis.com",
    "sheets.googleapis.com",
    "gmail.googleapis.com",
    "oauth2.googleapis.com",
    STORE_MYSHOPIFY_DOMAIN,
    REFUND_PROCESS_DOMAIN,
];

// ── Workflows (sheet · channels · league source) ────────────────────

export type WorkflowName = "waitlist" | "refund";

export interface SheetRef {
    spreadsheet_id: string;
    tab_name: string;
    tab_id: string;
}

export interface WorkflowConfig {
    sheet: SheetRef;
    /** Where the workflow's Slack channel is resolved from. */
    channels:
        | { source: "per_league" }
        | { source: "static"; test: string; review: string };
    /** Where league identity comes from. */
    leagueSource: "config" | "shopify";
}

export const WORKFLOWS: Record<WorkflowName, WorkflowConfig> = {
    waitlist: {
        sheet: {
            spreadsheet_id: envOr(
                "WAITLIST_SHEET_ID",
                "1QgyHDN9EcxqefEJCDozfLZ7QKVxSbOaW28WOET9PYEE",
            ),
            tab_name: "Form Responses 1",
            tab_id: "2072632661",
        },
        channels: { source: "per_league" },
        leagueSource: "config",
    },
    refund: {
        sheet: {
            spreadsheet_id: envOr(
                "REFUND_SHEET_ID",
                "11oXF8a7lZV0349QFVYyxPw8tEokoLJqZDrGDpzPjGtw",
            ),
            tab_name: "Refund_Requests",
            tab_id: "1435845892",
        },
        channels: { source: "static", test: REFUND_TEST_CHANNEL, review: REFUND_REVIEW_CHANNEL },
        leagueSource: "shopify",
    },
};

/** Resolve a workflow's sheet from the single workflow table. */
export function getWorkflowSheet(workflow: WorkflowName): SheetRef {
    return WORKFLOWS[workflow].sheet;
}

// ── Waitlist UI ─────────────────────────────────────────────────────

export const ENTRIES_PER_PAGE = 3;
export const SHEET_STATUS_FORMAT = "M/d 'at' h:mm aaa";

export const ACTION_OPTIONS = [
    { label: "No changes", value: "none" },
    { label: "Admit", value: "admit" },
    { label: "Remove", value: "remove" },
];

export const DROPDOWN_CAPTURE_CONFIG = {
    actionIdPrefix: "action_r",
    noneValues: ["none", "skip"],
};

// Per-player opt-in checkbox under each dropdown. Unticked by default, so the
// default action is "tag only, no email" — admitting tags the customer in
// Shopify but only sends the notification email when this box is checked. The
// label embeds the player's email and is built per-row in the modal.
export const CHECKBOX_CAPTURE_CONFIG = {
    actionIdPrefix: "email_r",
};

// ── Leagues ─────────────────────────────────────────────────────────

export interface LeagueConfig {
    channelId: string;
    sport: string;
    day: string;
    division: string;
    product_id: number;
    variant_ids: {
        veteran: number;
        early: number;
        general: number;
        waitlist: number;
    };
}

const LEAGUE_DATA: LeagueConfig[] = [
    {
        channelId: "C02HQ3WKC",
        sport: "bowling",
        day: "sunday",
        division: "open",
        product_id: 7590249070686,
        variant_ids: {
            veteran: 42526445371486,
            early: 42526445600862,
            general: 42526445633630,
            waitlist: 42526445666398,
        },
    },
    {
        channelId: "C0A5V3YU9JA",
        sport: "bowling",
        day: "monday",
        division: "wtnb",
        product_id: 7601480859742,
        variant_ids: {
            veteran: 42570173218910,
            early: 42570173251678,
            general: 42570173284446,
            waitlist: 42570173317214,
        },
    },
    {
        channelId: "C06G8UEBJ9X",
        sport: "bowling",
        day: "monday",
        division: "open",
        product_id: 7590248874078,
        variant_ids: {
            veteran: 42526444027998,
            early: 42526444060766,
            general: 42526444093534,
            waitlist: 42526444126302,
        },
    },
    {
        channelId: "C0878GTS7KK",
        sport: "dodgeball",
        day: "sunday",
        division: "wtnb",
        product_id: 7601038098526,
        variant_ids: {
            veteran: 42568007221342,
            early: 42568007254110,
            general: 42568007286878,
            waitlist: 42568007319646,
        },
    },
    {
        channelId: "C03872ZMGCV",
        sport: "dodgeball",
        day: "sunday",
        division: "open",
        product_id: 7600806395998,
        variant_ids: {
            veteran: 42567304904798,
            early: 42567305330782,
            general: 42567305363550,
            waitlist: 42567305396318,
        },
    },
    {
        channelId: "C02HP5P9Z",
        sport: "dodgeball",
        day: "monday",
        division: "open",
        product_id: 7601038131294,
        variant_ids: {
            veteran: 42568007352414,
            early: 42568007385182,
            general: 42568007417950,
            waitlist: 42568007450718,
        },
    },
    {
        channelId: "C06FTBYC5J9",
        sport: "dodgeball",
        day: "tuesday",
        division: "open",
        product_id: 7601097572446,
        variant_ids: {
            veteran: 42569080340574,
            early: 42569080373342,
            general: 42569080406110,
            waitlist: 42569080438878,
        },
    },
    {
        channelId: "C06G8UGC03B",
        sport: "dodgeball",
        day: "wednesday",
        division: "wtnb",
        product_id: 7601097998430,
        variant_ids: {
            veteran: 42569102688350,
            early: 42569102721118,
            general: 42569102753886,
            waitlist: 42569102786654,
        },
    },
    {
        channelId: "C06G8UGV00H",
        sport: "dodgeball",
        day: "thursday",
        division: "open",
        product_id: 7601098063966,
        variant_ids: {
            veteran: 42569103474782,
            early: 42569103507550,
            general: 42569103540318,
            waitlist: 42569103573086,
        },
    },
    {
        channelId: "C06FYP1KYPN",
        sport: "kickball",
        day: "sunday",
        division: "open",
        product_id: 7581465968734,
        variant_ids: {
            veteran: 42506023829598,
            early: 42506023895134,
            general: 42506023927902,
            waitlist: 42506023960670,
        },
    },
    {
        channelId: "C08DHA0LGJU",
        sport: "kickball",
        day: "monday",
        division: "open",
        product_id: 7587513565278,
        variant_ids: {
            veteran: 42519567302750,
            early: 42519567368286,
            general: 42519567401054,
            waitlist: 42519567433822,
        },
    },
    {
        channelId: "C04PFCKDSUA",
        sport: "kickball",
        day: "tuesday",
        division: "open",
        product_id: 7590021300318,
        variant_ids: {
            veteran: 42525453484126,
            early: 42525453516894,
            general: 42525453549662,
            waitlist: 42525453582430,
        },
    },
    {
        channelId: "C04PF901V35",
        sport: "kickball",
        day: "wednesday",
        division: "open",
        product_id: 7590021333086,
        variant_ids: {
            veteran: 42525453615198,
            early: 42525453647966,
            general: 42525453680734,
            waitlist: 42525453713502,
        },
    },
    {
        channelId: "C093689HNF7",
        sport: "kickball",
        day: "thursday",
        division: "wtnb",
        product_id: 7590021365854,
        variant_ids: {
            veteran: 42525453746270,
            early: 42525453779038,
            general: 42525453811806,
            waitlist: 42525453844574,
        },
    },
    {
        channelId: "C06NU1Z4FTK",
        sport: "kickball",
        day: "saturday",
        division: "wtnb",
        product_id: 7587512582238,
        variant_ids: {
            veteran: 42519558226014,
            early: 42519558258782,
            general: 42519558291550,
            waitlist: 42519558324318,
        },
    },
    {
        channelId: "C02HP5Q2R",
        sport: "kickball",
        day: "saturday",
        division: "open",
        product_id: 7590193332318,
        variant_ids: {
            veteran: 42526101045342,
            early: 42526101078110,
            general: 42526101110878,
            waitlist: 42526101143646,
        },
    },
    {
        channelId: "C09GF0Y3TDF",
        sport: "pickleball",
        day: "sunday",
        division: "wtnb",
        product_id: 7601479450718,
        variant_ids: {
            veteran: 42570170630238,
            early: 42570170663006,
            general: 42570170695774,
            waitlist: 42570170728542,
        },
    },
    {
        channelId: "C06M6GCF39U",
        sport: "pickleball",
        day: "tuesday",
        division: "open",
        product_id: 7601479483486,
        variant_ids: {
            veteran: 42570170761310,
            early: 42570170794078,
            general: 42570170826846,
            waitlist: 42570170859614,
        },
    },
    {
        channelId: "C0A60NFPR3N",
        sport: "pickleball",
        day: "thursday",
        division: "open",
        product_id: 7601479516254,
        variant_ids: {
            veteran: 42570170892382,
            early: 42570170925150,
            general: 42570170957918,
            waitlist: 42570170990686,
        },
    },
    {
        channelId: "C09FLDJK3SB",
        sport: "pickleball",
        day: "saturday",
        division: "open",
        product_id: 7601479417950,
        variant_ids: {
            veteran: 42570170499166,
            early: 42570170531934,
            general: 42570170564702,
            waitlist: 42570170597470,
        },
    },
];

export const CURRENT_LEAGUES: LeagueConfig[] = LEAGUE_DATA;

const CHANNEL_TO_LEAGUE = new Map(
    LEAGUE_DATA.map((lg) => [lg.channelId, buildLeagueKey(lg.sport, lg.day, lg.division)]),
);

export function getDefaultLeagueForChannel(channelId: string): string | undefined {
    return CHANNEL_TO_LEAGUE.get(channelId);
}

export function getLeague(
    sport: string,
    day: string,
    division: string,
): LeagueConfig | undefined {
    return LEAGUE_DATA.find(
        (lg) => lg.sport === sport && lg.day === day && lg.division === division,
    );
}

export function getDaysForSport(sport: string): { wtnb: string[]; open: string[] } {
    const wtnb = new Set<string>();
    const open = new Set<string>();
    for (const lg of LEAGUE_DATA) {
        if (lg.sport !== sport) continue;
        if (lg.division === "wtnb") wtnb.add(lg.day);
        else open.add(lg.day);
    }
    return { wtnb: [...wtnb], open: [...open] };
}
