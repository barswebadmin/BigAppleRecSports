export type Season = "winter" | "spring" | "summer" | "fall";
export const ALL_SEASONS: readonly Season[] = ["winter", "spring", "summer", "fall"];

export type VariantIds = {
    veteran: number;
    early: number;
    general: number;
    waitlist: number;
};

/** Single source of truth for all league fields. League and LeagueConfig are
 *  both Pick subsets of this. */
export interface LeagueFields {
    year: number;
    season: Season;
    sport: string;
    day: string;
    division: string;
    channelId: string;
    product_id: number;
    variant_ids: VariantIds;
}

export type League = Pick<LeagueFields, "year" | "season" | "sport" | "day" | "division">;
export type LeagueConfig = Pick<
    LeagueFields,
    "channelId" | "sport" | "day" | "division" | "product_id" | "variant_ids"
>;
