/**
 * In-process test harness: mock Slack client + fetch capture for hermetic
 * builder→executor regression tests (Stage 8). No real network or Deno.env.
 */

import { stub } from "@std/testing/mock";
import type { SlackAPIClient } from "deno-slack-api/types.ts";

export interface RecordedSlackCall {
    method: string;
    args: unknown;
}

export interface MockSlackClient {
    client: SlackAPIClient;
    calls: RecordedSlackCall[];
}

export function createMockSlackClient(): MockSlackClient {
    const calls: RecordedSlackCall[] = [];

    const record = (method: string, args: unknown) => {
        calls.push({ method, args });
    };

    const client = {
        chat: {
            postMessage: (args: Record<string, unknown>) => {
                record("chat.postMessage", args);
                return Promise.resolve({
                    ok: true,
                    ts: "1234567890.000001",
                    channel: args.channel as string,
                });
            },
            update: (args: Record<string, unknown>) => {
                record("chat.update", args);
                return Promise.resolve({
                    ok: true,
                    ts: args.ts as string,
                    channel: args.channel as string,
                });
            },
        },
        views: {
            open: (args: Record<string, unknown>) => {
                record("views.open", args);
                return Promise.resolve({ ok: true, view: { id: "V123" } });
            },
            update: (args: Record<string, unknown>) => {
                record("views.update", args);
                return Promise.resolve({ ok: true, view: { id: args.view_id as string } });
            },
        },
        functions: {
            completeSuccess: (args: Record<string, unknown>) => {
                record("functions.completeSuccess", args);
                return Promise.resolve({ ok: true });
            },
        },
    } as unknown as SlackAPIClient;

    return { client, calls };
}

export interface RecordedFetch {
    method: string;
    url: string;
    headers: Record<string, string>;
    body?: string;
}

export interface FetchMatcher {
    match: (url: string, method: string, body?: string) => boolean;
    response: Response | (() => Response | Promise<Response>);
}

export interface FetchStub {
    calls: RecordedFetch[];
    restore: () => void;
}

function headersToRecord(headers: Headers): Record<string, string> {
    const out: Record<string, string> = {};
    headers.forEach((value, key) => {
        out[key] = value;
    });
    return out;
}

/** Install a global fetch stub that records every call and returns canned responses. */
export function installFetchStub(matchers: FetchMatcher[]): FetchStub {
    const calls: RecordedFetch[] = [];
    const original = globalThis.fetch;

    const fetchStub = stub(
        globalThis,
        "fetch",
        async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
            const url = typeof input === "string"
                ? input
                : input instanceof URL
                ? input.href
                : input.url;
            const method = init?.method ?? (input instanceof Request ? input.method : "GET");
            const body = init?.body
                ? typeof init.body === "string" ? init.body : await new Response(init.body).text()
                : input instanceof Request
                ? await input.clone().text()
                : undefined;
            const headers = init?.headers
                ? headersToRecord(new Headers(init.headers))
                : input instanceof Request
                ? headersToRecord(input.headers)
                : {};

            calls.push({ method, url, headers, body: body || undefined });

            for (const matcher of matchers) {
                if (matcher.match(url, method, body)) {
                    const res = typeof matcher.response === "function"
                        ? await matcher.response()
                        : matcher.response;
                    return res.clone();
                }
            }

            return new Response(`No fetch stub for ${method} ${url}`, { status: 404 });
        },
    );

    return {
        calls,
        restore: () => {
            fetchStub.restore();
            globalThis.fetch = original;
        },
    };
}

/** PKCS8 RSA key used only in tests — signs JWTs against the stubbed OAuth endpoint. */
const TEST_PRIVATE_KEY = `-----BEGIN PRIVATE KEY-----
MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQCyL5rtLV8UfC0B
tgjDnPjQqnfkTIOKG4kGABHX6DfMLQH9hpM1ohg6DKFDvls7MfKQpXEkqYUv8Anc
DtW0Uh/8CQ48eGkrzNghGFOc5WfATW+fOBZg3MYHXWTIQsBkzLtNFYj8TCWEQKux
c8ThTuGzGqnwDU8Xeai9kgBqV/GYFxpExXx4WFEuYAH+CQlSK+DA4wKOgqmHLI2i
sCLzPKvunF+SX/SGAAC9RXMcYpRRDR6KBkeggB05F7Hg0RxOxxz5AhXSF4wFQ1TG
UBrMCMgnQQx8gJ3pvnZbox6dF4fn79qnvKwXMMM7aMf8pQTEnaa2BDPu3IeqkDLn
gUDfjadNAgMBAAECggEBAJawq9TpCf/JBEbuK3tCxSmzALGSA6xInRj19iEhwg5q
AcTmiphQ/SwagkdINN9a3kh1obnfo0NnPO9dnF1jFqmO/vsk2cyw8BcM+6k0WQnI
cx2z0TkZfF++G/1AdnTIr54BGFhGDXRLPOhVf6sLitRtOEpK9xhjStEHKFLHDQoR
FY9W0m1iKYCWRhR67FEZcsvRgOxpUWsKO/uHFC0B7E9cVRMAnC19TdtDsBnLVE3/
QDYGFrTA/Z0cBxCEa+z3nmTb/mdi0WoehhXpUNY4jUrSJeZ28GzxEe8fkyoULUPW
tROIX5fiHMt+sopsC3qyvqPg01yZLVCYWtz+tT88LgECgYEA5Klw0FAAwPC/IOIh
sOuwZ+GcR3dIlM8oiS4B/Z0ouajhTAkO6hs9j+s6dqFTsx3GqCjX385D2tK9Xvvk
RTlFdMmOMFEZ57ojX/AJssvtepLrl9uiRvGX2o0m4PIwzwB73KWO5zNdFzntrgnH
0/wfdnmyoyfKD49vFSYdbCplXV8CgYEAx31E2V3miLCfXtec2O+eocpEmkmU2AY5
o3fq+CmiUH4nGh3oxHCN1+AmuKY9E+23UhGh7lk4erkBeR44iITJu9wdteUMwFEc
e2TWMLkdzK1Qy944/KRWgMHXR2DRCOdvS48yjvCHwHzrcWhgV1RTWv6vnFGCKirF
RpldPkApjtMCgYBiYJPsy77HQ8y3NRMRrxVCXEqEZMmRXF8wRd8NYiQ3XHUx5WPJ
TNb7qFSK3XXJRjJF/uyBmZiP+MMIro7TSYScbmsCVqIylF7L09YYWqxdZACAYTo8
E40ltjzX4tsk9CxWDdShm/OdHosnqYWTqpFOw6UblO7WKvu7uZ5G/yaFOQKBgQCk
pUVPyepdYrkGhBoWCh75FYHtfVF1wh2MR4sM6v/mQ1hue8UDbIoFZCFRQRMkAYzO
FXN6zvSIhW0r07+BHWeKvy9eUv9lMwy44w7NA9wOc/U9bdnG2rPybQoLBWNBYBJB
YJyv0OGaAwAnh6gMK7LoZU/3SmaN+uL7U9TbbgVetQKBgERseC6x2tFyT9YiV1MU
MqnuXoq/XWATn2wvWrc5VgaIqJsMwg6wYKgYeguGg8GtEfK/OmGyxbuUBE5Nwd33
X3Q29tqbIRyIXlLpj/7riMwBB7CuH8REkWV1KbOcflz8kXmrMvdC5wQVQK+9pY0N
IhHo3Fet4FYYaIiGL165Y5B+
-----END PRIVATE KEY-----`;

export function createTestEnv(overrides: Record<string, string> = {}): Record<string, string> {
    return {
        SHOPIFY__URL__API_GRAPH_QL:
            "https://test-shop.myshopify.com/admin/api/2025-01/graphql.json",
        SHOPIFY__TOKEN__ADMIN: "test-shopify-token",
        GOOGLE__SERVICE_ACCOUNT: JSON.stringify({
            client_email: "test@test.iam.gserviceaccount.com",
            private_key: TEST_PRIVATE_KEY,
        }),
        ...overrides,
    };
}

export function oauthTokenResponse(): Response {
    return new Response(
        JSON.stringify({ access_token: "test-google-token", expires_in: 3600 }),
        { status: 200, headers: { "Content-Type": "application/json" } },
    );
}

export function gmailSendAsResponse(): Response {
    return new Response(JSON.stringify({ signature: "<p>Test signature</p>" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
    });
}

let _lastGqlBody = "{}";
let _sheetsUrl = "";

/** Fetch stub matchers for waitlist dry-run: OAuth, Sheets read, Shopify, Gmail. */
export function buildWaitlistFetchMatchers(opts: {
    productHandle: string;
    sheetRows: string[][];
}): FetchMatcher[] {
    return [
        {
            match: (url, method) =>
                method === "POST" && url.includes("oauth2.googleapis.com/token"),
            response: oauthTokenResponse,
        },
        {
            match: (url, method) => {
                if (method === "GET" && url.includes("sheets.googleapis.com")) {
                    _sheetsUrl = url;
                    return true;
                }
                return false;
            },
            response: () => {
                const values = _sheetsUrl.includes("A1%3AZ1") || _sheetsUrl.includes("A1:Z1")
                    ? [opts.sheetRows[0]]
                    : opts.sheetRows;
                return new Response(JSON.stringify({ values }), {
                    status: 200,
                    headers: { "Content-Type": "application/json" },
                });
            },
        },
        {
            match: (url, method) =>
                method === "POST" && url.includes("sheets.googleapis.com") &&
                (url.includes("batchUpdate") || url.includes(":append") || url.includes(":update")),
            response: () => new Response("unexpected sheet write in dry-run", { status: 500 }),
        },
        {
            match: (url) => url.includes("gmail.googleapis.com") && url.includes("/sendAs/"),
            response: gmailSendAsResponse,
        },
        {
            match: (url, method, body) => {
                if (method === "POST" && url.includes("myshopify.com") && body) {
                    _lastGqlBody = body;
                    return true;
                }
                return false;
            },
            response: () => {
                const parsed = JSON.parse(_lastGqlBody);
                const query = parsed.query as string;
                if (query.includes("products")) {
                    return new Response(
                        JSON.stringify({
                            data: {
                                products: {
                                    nodes: [{
                                        id: "gid://shopify/Product/999",
                                        handle: opts.productHandle,
                                        tags: [],
                                        variants: { nodes: [] },
                                    }],
                                },
                            },
                        }),
                        { status: 200, headers: { "Content-Type": "application/json" } },
                    );
                }
                if (query.includes("customers")) {
                    return new Response(
                        JSON.stringify({ data: { customers: { nodes: [] } } }),
                        { status: 200, headers: { "Content-Type": "application/json" } },
                    );
                }
                return new Response(JSON.stringify({ data: {} }), {
                    status: 200,
                    headers: { "Content-Type": "application/json" },
                });
            },
        },
    ];
}

export function isSheetWrite(call: RecordedFetch): boolean {
    if (!call.url.includes("sheets.googleapis.com")) return false;
    if (call.method === "PATCH" || call.method === "PUT") return true;
    return call.method === "POST" &&
        (call.url.includes("batchUpdate") ||
            call.url.includes(":append") ||
            call.url.includes(":update"));
}
