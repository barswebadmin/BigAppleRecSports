/**
 * Google API client — JWT service account auth with domain-wide delegation.
 * Token is fetched lazily and cached; re-auths automatically near expiry.
 */

import { importPKCS8, SignJWT } from "jose";
import { GOOGLE_API } from "../../config/store.ts";
import { DEFAULT_GMAIL_SENDER } from "./gmail.ts";

const TOKEN_URL = GOOGLE_API.oauth_token_url;
const SUBJECT = DEFAULT_GMAIL_SENDER.email_address;
const SCOPES = GOOGLE_API.scopes;

const SHEETS_BASE = GOOGLE_API.sheets_base;

/**
 * A sheet/tab handle. `id` is the numeric sheetId (the `gid` in the URL).
 *
 * Keep `id` even though the values API addresses ranges by name: the sheetId is
 * stable across tab renames, and the structural `spreadsheets.batchUpdate` API
 * (formatting, insert/delete rows, conditional formatting, protected ranges,
 * sort/filter) references sheets by sheetId — never by name. It's also what
 * builds the tab deep-link URL. See docs/reference/libraries/google-sheets-api.md.
 */
export interface SheetTab {
    name: string;
    id: string;
}

/**
 * A single cell write. `row` is 1-based (matches A1 + the parser's rowNumber);
 * `col` is 0-based (matches `findColumn` and the structural API's GridRange,
 * whose indexes are all zero-based). The 0-based index is the canonical column
 * form; `columnToLetter` adapts it to A1 only at the values-API boundary.
 */
export interface CellUpdate {
    row: number;
    col: number;
    value: string;
}

/** 0-based column index → A1 letter (0→A, 25→Z, 26→AA). */
export function columnToLetter(index: number): string {
    let n = index;
    let letter = "";
    do {
        letter = String.fromCodePoint(65 + (n % 26)) + letter;
        n = Math.floor(n / 26) - 1;
    } while (n >= 0);
    return letter;
}

export class GoogleClient {
    private sa: { client_email: string; private_key: string };
    private token: string | null = null;
    private expiresAt = 0;

    constructor(saJson: string) {
        this.sa = JSON.parse(saJson);
    }

    async getRequestHeaders(): Promise<Record<string, string>> {
        if (!this.token || this.expiresAt < Date.now() + 60_000) {
            const { token, expiresIn } = await this.exchangeJwtForToken();
            this.token = token;
            this.expiresAt = Date.now() + expiresIn * 1000;
        }
        return { Authorization: `Bearer ${this.token}` };
    }

    private async exchangeJwtForToken(): Promise<{ token: string; expiresIn: number }> {
        const key = await importPKCS8(this.sa.private_key, "RS256");

        const jwt = await new SignJWT({ scope: SCOPES.join(" ") })
            .setProtectedHeader({ alg: "RS256", typ: "JWT" })
            .setIssuer(this.sa.client_email)
            .setSubject(SUBJECT)
            .setAudience(TOKEN_URL)
            .setIssuedAt()
            .setExpirationTime("1h")
            .sign(key);

        const res = await fetch(TOKEN_URL, {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: new URLSearchParams({
                grant_type: "urn:ietf:params:oauth:grant-type:jwt-bearer",
                assertion: jwt,
            }),
        });

        if (!res.ok) {
            throw new Error(`Token exchange failed (${res.status}): ${await res.text()}`);
        }
        const data = await res.json();
        return { token: data.access_token, expiresIn: data.expires_in };
    }

    /** Read a tab's values (rows with an empty first cell are dropped). */
    async getSpreadsheet(
        spreadsheetId: string,
        tab: SheetTab,
        columns: string,
    ): Promise<{ url: string; values: string[][] }> {
        const range = encodeURIComponent(`'${tab.name}'!${columns}`);
        const url = `${SHEETS_BASE}/${spreadsheetId}/values/${range}`;
        const headers = await this.getRequestHeaders();
        const res = await fetch(url, { headers });
        if (!res.ok) throw new Error(`Sheets GET failed (${res.status}): ${await res.text()}`);
        const data = await res.json();
        const allRows = ((data.values as string[][]) ?? []).filter(
            (row) => row[0] && row[0].trim() !== "",
        );
        return { url: this.spreadsheetUrl(spreadsheetId, tab), values: allRows };
    }

    /**
     * Write any number of individual cells in a single `values:batchUpdate`
     * request (RAW input mode). Callers pass row/col indices; the A1 ranges are
     * built here so column-letter math stays in one place. No-op for an empty list.
     */
    async updateCells(
        spreadsheetId: string,
        tabName: string,
        updates: CellUpdate[],
    ): Promise<void> {
        if (updates.length === 0) return;
        const url = `${SHEETS_BASE}/${spreadsheetId}/values:batchUpdate`;
        const headers = await this.getRequestHeaders();
        const data = updates.map((u) => ({
            range: `'${tabName}'!${columnToLetter(u.col)}${u.row}`,
            values: [[u.value]],
        }));
        const res = await fetch(url, {
            method: "POST",
            headers: { ...headers, "Content-Type": "application/json" },
            body: JSON.stringify({ valueInputOption: "RAW", data }),
        });
        if (!res.ok) {
            throw new Error(`Sheets batchUpdate failed (${res.status}): ${await res.text()}`);
        }
    }

    private spreadsheetUrl(spreadsheetId: string, tab: SheetTab): string {
        return `https://docs.google.com/spreadsheets/d/${spreadsheetId}/edit?gid=${tab.id}#gid=${tab.id}`;
    }
}

let _instance: GoogleClient | null = null;

export function getOrCreateGoogleClient(env: Record<string, string>): GoogleClient {
    if (!_instance) _instance = new GoogleClient(env.GOOGLE__SERVICE_ACCOUNT);
    return _instance;
}
