import { DefineType, Schema } from "deno-slack-sdk/mod.ts";

export const LeagueType = DefineType({
    name: "league",
    type: Schema.types.object,
    properties: {
        year: { type: Schema.types.integer },
        season: { type: Schema.types.string },
        sport: { type: Schema.types.string },
        day: { type: Schema.types.string },
        division: { type: Schema.types.string },
    },
    required: ["year", "season", "sport", "day", "division"],
});

export type League = {
    year: number;
    season: string;
    sport: string;
    day: string;
    division: string;
};
