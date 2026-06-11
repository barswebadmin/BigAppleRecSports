/**
 * Google API client — JWT service account auth with domain-wide delegation.
 * Token is fetched lazily and cached; re-auths automatically near expiry.
 */

import { importPKCS8, SignJWT } from "jose";

const TOKEN_URL = "https://oauth2.googleapis.com/token";
const SUBJECT = "web@bigapplerecsports.com";
const SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://mail.google.com/"];

const SHEETS_BASE = "https://sheets.googleapis.com/v4/spreadsheets";

export interface SheetTab {
    name: string;
    id: string;
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

    /** Write values starting at a cell (RAW input mode). */
    async updateSpreadsheet(
        spreadsheetId: string,
        tab: SheetTab,
        cell: string,
        values: string[][],
    ): Promise<{ url: string }> {
        const range = encodeURIComponent(`'${tab.name}'!${cell}`);
        const url = `${SHEETS_BASE}/${spreadsheetId}/values/${range}?valueInputOption=RAW`;
        const headers = await this.getRequestHeaders();
        const res = await fetch(url, {
            method: "PUT",
            headers: { ...headers, "Content-Type": "application/json" },
            body: JSON.stringify({ values }),
        });
        if (!res.ok) throw new Error(`Sheets PUT failed (${res.status}): ${await res.text()}`);
        return { url: this.spreadsheetUrl(spreadsheetId, tab) };
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
