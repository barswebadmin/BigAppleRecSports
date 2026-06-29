/**
 * Generic BARS API HTTP client. Refund-agnostic — exposes a small
 * `post<T>` / `get<T>` surface against any backend endpoint. Refund-specific
 * call sites build the request body inline using wire-shape types from
 * `domain/refund/types.ts` and call `post<T>` directly. There is no
 * refund-coupled HTTP wrapper.
 *
 * Defaults:
 *   - Base URL from env `BARS_API_URL` (no trailing slash)
 *   - `Content-Type: application/json`
 *   - `Accept: application/json`
 *   - `X-API-Key` from env `BARS_API_KEY` when set; omitted entirely when unset.
 *     A missing key is intentionally a no-op so deploys without the header
 *     surface as 401s from the backend rather than client-side throws (D22).
 *
 * Errors: any non-2xx response throws an Error whose message includes the
 * status code, the endpoint, and a truncated excerpt of the response body so
 * operators can self-diagnose without re-running the call.
 */

export interface BarsApiPostArgs {
  /** Path like `/refunds/validate`; joined with the base URL inside the client. */
  endpoint: string;
  /** Optional query-string params; values are URL-encoded by the client. */
  params?: Record<string, string>;
  /** Optional JSON request body. */
  body?: unknown;
  /** Additional headers; merged into (and override) the defaults. */
  headers?: Record<string, string>;
}

export interface BarsApiGetArgs {
  endpoint: string;
  params?: Record<string, string>;
  headers?: Record<string, string>;
}

export interface BarsApiClient {
  post<T>(args: BarsApiPostArgs): Promise<T>;
  get<T>(args: BarsApiGetArgs): Promise<T>;
}

const BODY_EXCERPT_LIMIT = 500;

function readEnv(env: Record<string, string>, key: string): string | undefined {
  const value = env[key];
  if (value !== undefined && value.trim() !== "") return value;
  try {
    const fromDeno = Deno.env.get(key);
    return fromDeno && fromDeno.trim() !== "" ? fromDeno : undefined;
  } catch {
    return undefined;
  }
}

function defaultHeaders(env: Record<string, string>): Record<string, string> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "application/json",
  };
  const apiKey = readEnv(env, "BARS_API_KEY");
  if (apiKey) headers["X-API-Key"] = apiKey;
  return headers;
}

function joinBase(baseUrl: string, endpoint: string): string {
  const trimmedBase = baseUrl.replace(/\/+$/, "");
  const path = endpoint.startsWith("/") ? endpoint : `/${endpoint}`;
  return `${trimmedBase}${path}`;
}

function buildUrl(
  baseUrl: string,
  endpoint: string,
  params?: Record<string, string>,
): string {
  const url = joinBase(baseUrl, endpoint);
  if (!params || Object.keys(params).length === 0) return url;
  const qs = new URLSearchParams(params).toString();
  return `${url}${url.includes("?") ? "&" : "?"}${qs}`;
}

async function readBodyExcerpt(res: Response): Promise<string> {
  try {
    const text = await res.text();
    return text.length > BODY_EXCERPT_LIMIT
      ? `${text.slice(0, BODY_EXCERPT_LIMIT)}…`
      : text;
  } catch {
    return "<unreadable response body>";
  }
}

async function parseJson<T>(res: Response, endpoint: string): Promise<T> {
  const raw = await res.text();
  if (!raw) return undefined as unknown as T;
  try {
    return JSON.parse(raw) as T;
  } catch (err) {
    throw new Error(
      `BarsApiClient: failed to parse JSON response from ${endpoint} (${res.status}): ${String(
        err,
      )}`,
    );
  }
}

async function performRequest<T>(
  method: "GET" | "POST",
  baseUrl: string,
  headers: Record<string, string>,
  args: BarsApiPostArgs | BarsApiGetArgs,
  serializedBody: string | undefined,
): Promise<T> {
  const url = buildUrl(baseUrl, args.endpoint, args.params);
  const mergedHeaders = { ...headers, ...(args.headers ?? {}) };

  const res = await fetch(url, {
    method,
    headers: mergedHeaders,
    ...(serializedBody !== undefined ? { body: serializedBody } : {}),
  });

  if (!res.ok) {
    const excerpt = await readBodyExcerpt(res);
    throw new Error(
      `BarsApiClient: ${method} ${args.endpoint} failed (status ${res.status}): ${excerpt}`,
    );
  }
  return await parseJson<T>(res, args.endpoint);
}

/**
 * Construct a BARS API client. The `env` map is passed in (rather than read
 * from `Deno.env` directly) so callers can inject a fake during tests; the
 * fallback to `Deno.env.get` covers the runtime case where Slack-app handlers
 * receive `inputs.env` already populated.
 */
export function makeBarsApiClient(env: Record<string, string>): BarsApiClient {
  const rawBase = readEnv(env, "BARS_API_URL");
  if (!rawBase) {
    throw new Error(
      "BarsApiClient: BARS_API_URL is not set — configure the env var before invoking the client.",
    );
  }
  const baseUrl = rawBase.replace(/\/+$/, "");
  const headers = defaultHeaders(env);

  return {
    async post<T>(args: BarsApiPostArgs): Promise<T> {
      const body =
        args.body !== undefined ? JSON.stringify(args.body) : undefined;
      return await performRequest<T>("POST", baseUrl, headers, args, body);
    },
    async get<T>(args: BarsApiGetArgs): Promise<T> {
      return await performRequest<T>("GET", baseUrl, headers, args, undefined);
    },
  };
}
