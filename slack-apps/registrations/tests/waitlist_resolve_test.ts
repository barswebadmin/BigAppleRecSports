import { assertEquals } from "@std/assert";
import { resolveWaitlistOrder } from "../functions/resolve_waitlist_order.ts";
import type { LeagueWaitlists } from "../lib/waitlists/handlers/waitlist_entry_types.ts";

const waitlists: LeagueWaitlists = {
    leagues: {
        "kickball|sunday|open": {
            total: 1,
            entries: [{
                rowNumber: 5,
                position: 1,
                createdAt: "2026-01-01",
                sport: "kickball",
                day: "sunday",
                division: "open",
                firstName: "Jane",
                lastName: "Doe",
                emailAddress: "jane@example.com",
            }],
        },
    },
    byEmail: {},
    url: "https://docs.google.com/spreadsheets/d/test",
};

const signupBody = {
    email_address: "jane@example.com",
    sport: "kickball",
    day: "sunday",
    division: "open",
    order_number: "1001",
};

Deno.test("resolve_waitlist_order matches email to order action", () => {
    const result = resolveWaitlistOrder({
        body: JSON.stringify(signupBody),
        waitlists_json: JSON.stringify(waitlists),
    });

    assertEquals(JSON.parse(result.outputs.actions_json), [{
        type: "order",
        rowNumber: "5",
        firstName: "Jane",
        emailAddress: "jane@example.com",
    }]);
});

Deno.test("resolve_waitlist_order returns empty array for non-matching email", () => {
    const result = resolveWaitlistOrder({
        body: JSON.stringify({ ...signupBody, email_address: "nobody@example.com" }),
        waitlists_json: JSON.stringify(waitlists),
    });
    assertEquals(result.outputs.actions_json, "[]");
});

Deno.test("resolve_waitlist_order returns empty array for missing league", () => {
    const result = resolveWaitlistOrder({
        body: JSON.stringify({ ...signupBody, sport: "bowling" }),
        waitlists_json: JSON.stringify(waitlists),
    });
    assertEquals(result.outputs.actions_json, "[]");
});

Deno.test("resolve_waitlist_order returns empty array for invalid body JSON", () => {
    const result = resolveWaitlistOrder({
        body: "not-json",
        waitlists_json: JSON.stringify(waitlists),
    });
    assertEquals(result.outputs.actions_json, "[]");
});
