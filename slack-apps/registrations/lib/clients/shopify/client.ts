/**
 * Shopify Admin GraphQL client — thin transport layer with typed response classification.
 *
 * `gql<T>()` keeps its legacy `{data, errors: string[]}` shape for existing callers.
 * `gqlClassified<T>()` returns a typed discriminated union matching Python's
 * `parse_shopify_response` semantics (FORBIDDEN / BAD_REQUEST / UNPROCESSABLE_ENTITY /
 * NOT_ACCEPTABLE / NO_CONTENT / OK / UNEXPECTED_ERROR).
 */

export type ShopifyResponseKind =
    | "OK"
    | "NO_CONTENT"
    | "FORBIDDEN"
    | "BAD_REQUEST"
    | "UNPROCESSABLE_ENTITY"
    | "NOT_ACCEPTABLE"
    | "UNEXPECTED_ERROR";

export type ShopifyResponse<T> =
    | { kind: "OK"; data: T }
    | { kind: "NO_CONTENT"; data: T }
    | { kind: "FORBIDDEN"; errors: string[] }
    | { kind: "BAD_REQUEST"; errors: string[] }
    | { kind: "UNPROCESSABLE_ENTITY"; errors: string[] }
    | { kind: "NOT_ACCEPTABLE"; errors: string[] }
    | { kind: "UNEXPECTED_ERROR"; errors: string[] };

interface ShopifyError {
    message: string;
    extensions?: {
        code?: string;
        typeName?: string;
        fieldName?: string;
    };
}

interface ShopifySearchExtension {
    warnings?: { field: string; message: string }[];
}

interface ShopifyResponseBody {
    data?: unknown;
    errors?: ShopifyError[];
    extensions?: {
        search?: ShopifySearchExtension[];
    };
}

function hasValues(obj: unknown): boolean {
    if (obj === null || obj === undefined) return false;
    if (typeof obj === "string") return obj.length > 0;
    if (Array.isArray(obj)) return obj.some(hasValues);
    if (typeof obj === "object") return Object.values(obj).some(hasValues);
    return true;
}

export function parseShopifyResponse<T>(
    body: ShopifyResponseBody,
): ShopifyResponse<T> {
    const errors = body.errors ?? [];
    const data = body.data;
    const extensions = body.extensions ?? {};

    if (errors.length > 0 && data == null) {
        if (errors.some((e) => e.extensions?.code === "ACCESS_DENIED")) {
            return { kind: "FORBIDDEN", errors: errors.map((e) => e.message) };
        }
        if (
            errors.some(
                (e) =>
                    e.extensions?.code !== undefined &&
                    e.extensions?.typeName !== undefined &&
                    e.extensions?.fieldName !== undefined,
            )
        ) {
            return {
                kind: "UNPROCESSABLE_ENTITY",
                errors: errors.map((e) => e.message),
            };
        }
        return { kind: "BAD_REQUEST", errors: errors.map((e) => e.message) };
    }

    if (data && !hasValues(data)) {
        const searchEntries = extensions.search ?? [];
        if (searchEntries.some((s) => (s.warnings ?? []).length > 0)) {
            const warnings = searchEntries.flatMap((s) =>
                (s.warnings ?? []).map((w) => `${w.field}: ${w.message}`)
            );
            return { kind: "NOT_ACCEPTABLE", errors: warnings };
        }
        return { kind: "NO_CONTENT", data: data as T };
    }

    if (data && hasValues(data)) {
        return { kind: "OK", data: data as T };
    }

    return { kind: "UNEXPECTED_ERROR", errors: ["Unable to classify response"] };
}

export class ShopifyClient {
    private url: string;
    private token: string;

    constructor(url: string, token: string) {
        this.url = url;
        this.token = token;
    }

    async gql<T>(
        query: string,
        variables: Record<string, unknown>,
    ): Promise<{ data: T | null; errors: string[] }> {
        const body = await this.post(query, variables);
        const topErrors = body.errors?.map((e) => e.message) ?? [];
        console.log("[shopify:gql] errors:", topErrors.length);
        if (topErrors.length > 0 && body.data == null) {
            return { data: null, errors: topErrors };
        }
        return { data: (body.data ?? null) as T | null, errors: [] };
    }

    async gqlClassified<T>(
        query: string,
        variables: Record<string, unknown>,
    ): Promise<ShopifyResponse<T>> {
        const body = await this.post(query, variables);
        const result = parseShopifyResponse<T>(body);
        console.log("[shopify:gqlClassified]", result.kind);
        return result;
    }

    private async post(
        query: string,
        variables: Record<string, unknown>,
    ): Promise<ShopifyResponseBody> {
        const res = await fetch(this.url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-Shopify-Access-Token": this.token,
            },
            body: JSON.stringify({ query, variables }),
        });
        return await res.json() as ShopifyResponseBody;
    }
}

export function createShopifyClient(
    env: Record<string, string>,
): ShopifyClient {
    const url = env.SHOPIFY__URL__API_GRAPH_QL;
    const token = env.SHOPIFY__TOKEN__ADMIN;
    if (!url || !token) {
        throw new Error(
            "Shopify client not configured — missing SHOPIFY__URL__API_GRAPH_QL or SHOPIFY__TOKEN__ADMIN",
        );
    }
    return new ShopifyClient(url, token);
}
