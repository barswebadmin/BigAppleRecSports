import { assertEquals } from "@std/assert";
import { resolveWaitlistOrder } from "../../domain/waitlist/resolve.ts";
import type { LeagueWaitlists } from "../../domain/waitlist/types.ts";

const waitlists: LeagueWaitlists = {
    leagues: {
        "kickball|sunday|open": {
            total: 1,
            entries: [{
                rowNumber: 5,
                position: 1,
                createdAt: "2026-01-01",
                league: {
                    year: 2026,
                    season: "Winter",
                    sport: "kickball",
                    day: "sunday",
                    division: "open",
                },
                firstName: "Jane",
                lastName: "Doe",
                emailAddress: "jane@example.com",
            }],
        },
    },
    byEmail: {},
    url: "https://docs.google.com/spreadsheets/d/test",
    statusColumnIndex: 9,
};

const signupBody = {
    email: "jane@example.com",
    sport: "kickball",
    day: "sunday",
    division: "open",
    order_number: "1001",
};

Deno.test("resolve_waitlist_order matches email to order action", () => {
    const actions = resolveWaitlistOrder({
        body: JSON.stringify(signupBody),
        waitlists_json: JSON.stringify(waitlists),
    });

    assertEquals(actions, [{
        type: "order",
        rowNumber: "5",
        firstName: "Jane",
        emailAddress: "jane@example.com",
    }]);
});

Deno.test("resolve_waitlist_order returns empty array for non-matching email", () => {
    const actions = resolveWaitlistOrder({
        body: JSON.stringify({ ...signupBody, email: "nobody@example.com" }),
        waitlists_json: JSON.stringify(waitlists),
    });
    assertEquals(actions, []);
});

Deno.test("resolve_waitlist_order returns empty array for missing league", () => {
    const actions = resolveWaitlistOrder({
        body: JSON.stringify({ ...signupBody, sport: "bowling" }),
        waitlists_json: JSON.stringify(waitlists),
    });
    assertEquals(actions, []);
});

Deno.test("resolve_waitlist_order returns empty array for invalid body JSON", () => {
    const actions = resolveWaitlistOrder({
        body: "not-json",
        waitlists_json: JSON.stringify(waitlists),
    });
    assertEquals(actions, []);
});
