import { assertEquals, assertExists } from "@std/assert";
import { processSelections } from "../functions/handle_waitlist_actions.ts";
import { formatProductHandle } from "../utils/formatters.ts";
import { leagueFromKey } from "../lib/waitlists/league_key.ts";
import {
    buildWaitlistFetchMatchers,
    createMockSlackClient,
    createTestEnv,
    installFetchStub,
    isSheetWrite,
} from "./harness.ts";

const leagueKey = "kickball|sunday|open";
const league = leagueFromKey(leagueKey);
const productHandle = formatProductHandle(league);
const waitlistTag = `${productHandle}-waitlist`;

const sheetRows = [
    [
        "Timestamp",
        "League",
        "First Name",
        "Last Name",
        "Email Address",
        "Phone Number",
        "Gender",
        "Pronouns",
        "Status",
    ],
    [
        "1/1/2026",
        "kickball-sunday-open",
        "Jane",
        "Doe",
        "jane@example.com",
        "555-0100",
        "",
        "",
        "",
    ],
];

Deno.test("waitlist dry-run posts previews, builds tag+email requests, no sheet writes", async () => {
    const fetchStub = installFetchStub(
        buildWaitlistFetchMatchers({ productHandle, sheetRows }),
    );
    const { client, calls } = createMockSlackClient();
    const env = createTestEnv();

    try {
        await processSelections(
            {
                ch: "C_TEST_CHANNEL",
                league: leagueKey,
                sel: { "2": "admit" },
                email: { "2": true },
                dry: true,
            },
            { function_data: { execution_id: "Fx_TEST" }, user: { id: "U_TEST" } },
            client,
            env,
        );

        const postMessages = calls.filter((c) => c.method === "chat.postMessage");
        assertEquals(postMessages.length >= 1, true);
        const previewText = (postMessages[0].args as { text: string }).text;
        assertEquals(previewText.includes("DRY RUN"), true);

        const complete = calls.find((c) => c.method === "functions.completeSuccess");
        assertExists(complete);
        const outputs = (complete.args as { outputs: { actions_json: string } }).outputs;
        const actions = JSON.parse(outputs.actions_json);
        assertEquals(actions.length, 1);
        assertEquals(actions[0].type, "admit");
        assertEquals(actions[0].emailAddress, "jane@example.com");

        const shopifyMutations = fetchStub.calls.filter(
            (c) => c.url.includes("myshopify.com") && c.body?.includes("customerCreate"),
        );
        assertEquals(shopifyMutations.length, 0);

        const gqlBodies = fetchStub.calls
            .filter((c) => c.url.includes("myshopify.com") && c.body)
            .map((c) => JSON.parse(c.body!));

        const customerSearch = gqlBodies.find((b) => (b.query as string).includes("customers"));
        assertExists(customerSearch);

        const previewBlocks = (postMessages[0].args as { blocks: { type: string }[] }).blocks;
        const blockText = JSON.stringify(previewBlocks);
        assertEquals(blockText.includes(waitlistTag), true);
        assertEquals(blockText.includes("Send email notification"), true);

        const sheetWrites = fetchStub.calls.filter(isSheetWrite);
        assertEquals(sheetWrites.length, 0);

        const gmailSends = fetchStub.calls.filter(
            (c) => c.url.includes("gmail.googleapis.com") && c.url.includes("/messages/send"),
        );
        assertEquals(gmailSends.length, 0);
    } finally {
        fetchStub.restore();
    }
});

Deno.test("waitlist dry-run with email off skips email step in preview", async () => {
    const fetchStub = installFetchStub(
        buildWaitlistFetchMatchers({ productHandle, sheetRows }),
    );
    const { client, calls } = createMockSlackClient();
    const env = createTestEnv();

    try {
        await processSelections(
            {
                ch: "C_TEST_CHANNEL",
                league: leagueKey,
                sel: { "2": "admit" },
                email: {},
                dry: true,
            },
            { function_data: { execution_id: "Fx_TEST2" } },
            client,
            env,
        );

        const postMessages = calls.filter((c) => c.method === "chat.postMessage");
        assertEquals(postMessages.length >= 1, true);
        const blockText = JSON.stringify((postMessages[0].args as { blocks: unknown }).blocks);
        assertEquals(blockText.includes("no email will be sent"), true);
        assertEquals(fetchStub.calls.filter(isSheetWrite).length, 0);
    } finally {
        fetchStub.restore();
    }
});
