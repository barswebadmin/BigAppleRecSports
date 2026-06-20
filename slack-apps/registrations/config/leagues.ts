/**
 * Raw league catalog for the current season.
 * Each row: channelId, sport, day, division, product_id, veteran, early, general, waitlist
 * Update variant IDs each season by pulling them from Shopify admin.
 */

export type LeagueRow = [
    channelId: string,
    sport: string,
    day: string,
    division: string,
    product_id: number,
    veteran: number,
    early: number,
    general: number,
    waitlist: number,
];

// deno-fmt-ignore
export const LEAGUE_ROWS: LeagueRow[] = [
    //  channelId          sport           day           division   product_id       veteran          early            general          waitlist
    ["C02HQ3WKC",       "bowling",      "sunday",      "open",    7590249070686,   42526445371486,  42526445600862,  42526445633630,  42526445666398],
    ["C0A5V3YU9JA",     "bowling",      "monday",      "wtnb",    7601480859742,   42570173218910,  42570173251678,  42570173284446,  42570173317214],
    ["C06G8UEBJ9X",     "bowling",      "monday",      "open",    7590248874078,   42526444027998,  42526444060766,  42526444093534,  42526444126302],
    ["C0878GTS7KK",     "dodgeball",    "sunday",      "wtnb",    7601038098526,   42568007221342,  42568007254110,  42568007286878,  42568007319646],
    ["C03872ZMGCV",     "dodgeball",    "sunday",      "open",    7600806395998,   42567304904798,  42567305330782,  42567305363550,  42567305396318],
    ["C02HP5P9Z",       "dodgeball",    "monday",      "open",    7601038131294,   42568007352414,  42568007385182,  42568007417950,  42568007450718],
    ["C06FTBYC5J9",     "dodgeball",    "tuesday",     "open",    7601097572446,   42569080340574,  42569080373342,  42569080406110,  42569080438878],
    ["C06G8UGC03B",     "dodgeball",    "wednesday",   "wtnb",    7601097998430,   42569102688350,  42569102721118,  42569102753886,  42569102786654],
    ["C06G8UGV00H",     "dodgeball",    "thursday",    "open",    7601098063966,   42569103474782,  42569103507550,  42569103540318,  42569103573086],
    ["C06FYP1KYPN",     "kickball",     "sunday",      "open",    7581465968734,   42506023829598,  42506023895134,  42506023927902,  42506023960670],
    ["C08DHA0LGJU",     "kickball",     "monday",      "open",    7587513565278,   42519567302750,  42519567368286,  42519567401054,  42519567433822],
    ["C04PFCKDSUA",     "kickball",     "tuesday",     "open",    7590021300318,   42525453484126,  42525453516894,  42525453549662,  42525453582430],
    ["C04PF901V35",     "kickball",     "wednesday",   "open",    7590021333086,   42525453615198,  42525453647966,  42525453680734,  42525453713502],
    ["C093689HNF7",     "kickball",     "thursday",    "wtnb",    7590021365854,   42525453746270,  42525453779038,  42525453811806,  42525453844574],
    ["C06NU1Z4FTK",     "kickball",     "saturday",    "wtnb",    7587512582238,   42519558226014,  42519558258782,  42519558291550,  42519558324318],
    ["C02HP5Q2R",       "kickball",     "saturday",    "open",    7590193332318,   42526101045342,  42526101078110,  42526101110878,  42526101143646],
    ["C09GF0Y3TDF",     "pickleball",   "sunday",      "wtnb",    7601479450718,   42570170630238,  42570170663006,  42570170695774,  42570170728542],
    ["C06M6GCF39U",     "pickleball",   "tuesday",     "open",    7601479483486,   42570170761310,  42570170794078,  42570170826846,  42570170859614],
    ["C0A60NFPR3N",     "pickleball",   "thursday",    "open",    7601479516254,   42570170892382,  42570170925150,  42570170957918,  42570170990686],
    ["C09FLDJK3SB",     "pickleball",   "saturday",    "open",    7601479417950,   42570170499166,  42570170531934,  42570170564702,  42570170597470],
];
