// ── Season ──────────────────────────────────────────────────────────

export const CURRENT_YEAR = 2026;
export const CURRENT_SEASON = "spring";

export type Season = "winter" | "spring" | "summer" | "fall";
export const ALL_SEASONS: Season[] = ["winter", "spring", "summer", "fall"];

// ── URLs ────────────────────────────────────────────────────────────

export const BARS_URLS = {
    website: "https://www.bigapplerecsports.com",
    admin_ui: "https://admin.shopify.com/store/09fe59-3",
    admin_api: "https://09fe59-3/admin/api/2025-01/graphql.json",
};

// ── Gmail ───────────────────────────────────────────────────────────

export const DEFAULT_GMAIL_SENDER = {
    name: "Big Apple Rec Sports",
    email_address: "web@bigapplerecsports.com",
};

// ── Google Sheets ───────────────────────────────────────────────────

export const GOOGLE_SHEETS = {
    waitlists: {
        spreadsheet_id: "1KcHgBHyeLmL3MQjbkB5CJUNFXbYMrtqZFqOsVnL0id0",
        tab_name: "Form Responses",
        tab_id: "309697269",
    },
    refund_requests: {
        spreadsheet_id: "11oXF8a7lZV0349QFVYyxPw8tEokoLJqZDrGDpzPjGtw",
        tab_name: "Refund_Requests",
        tab_id: "1435845892",
    },
};

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
    LEAGUE_DATA.map((lg) => [lg.channelId, `${lg.sport}|${lg.day}|${lg.division}`]),
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
