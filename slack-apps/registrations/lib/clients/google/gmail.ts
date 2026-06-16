/**
 * Gmail API operations — raw fetch, no external dependencies.
 */

import type { GoogleClient } from "./client.ts";
import type { EmailMessage } from "./types/email_message.ts";
import type { PreparedRequest } from "../prepared_request.ts";
import { GOOGLE_API } from "../../../config.ts";

const BASE = GOOGLE_API.gmail_base;
const log = (fn: string, ...args: unknown[]) => console.log(`[gmail:${fn}]`, ...args);

const FALLBACK_SIGNATURE = `
<div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; font-size: 14px;">
  <p>Warmly,<br><b>BARS Leadership</b></p>
  <p><strong>Big Apple Rec Sports</strong><br>
  Follow us: <a href="https://www.instagram.com/bigapplerecsports/">Instagram</a> | <a href="https://www.facebook.com/groups/bigapplerecsports">Facebook</a></p>
</div>`;

const signatureCache = new Map<string, string>();

async function fetchSignature(client: GoogleClient, sendAsEmail: string): Promise<string> {
    const cached = signatureCache.get(sendAsEmail);
    if (cached !== undefined) return cached;

    try {
        const headers = await client.getRequestHeaders();
        const res = await fetch(
            `${BASE}/users/me/settings/sendAs/${encodeURIComponent(sendAsEmail)}`,
            { headers },
        );
        if (res.ok) {
            const data = await res.json();
            const sig = (data.signature as string) || "";
            if (sig) {
                log("fetchSignature", `fetched for ${sendAsEmail} (${sig.length} chars)`);
                signatureCache.set(sendAsEmail, sig);
                return sig;
            }
        }
    } catch (e) {
        log("fetchSignature", `failed for ${sendAsEmail}, using fallback:`, e);
    }

    signatureCache.set(sendAsEmail, FALLBACK_SIGNATURE);
    return FALLBACK_SIGNATURE;
}

/** Compose the raw RFC 2822 message (headers + HTML body + signature). */
function composeRfc2822(msg: EmailMessage, signature: string): string {
    const from = `"${msg.sendAs.name}" <${msg.sendAs.emailAddress}>`;
    const headers = [
        `From: ${from}`,
        `To: ${msg.to}`,
        `Subject: ${msg.subject}`,
        `MIME-Version: 1.0`,
        `Content-Type: text/html; charset=UTF-8`,
        ...(msg.replyTo ? [`Reply-To: ${msg.replyTo}`] : []),
        ...(msg.cc ? [`Cc: ${msg.cc}`] : []),
        ...(msg.bcc ? [`Bcc: ${msg.bcc}`] : []),
    ].join("\r\n");

    const body = msg.htmlBodyParts.map((p) => `<p>${p}</p>`).join("\n");
    const html = signature ? `${body}\n<br><br>${signature}` : body;
    return `${headers}\r\n\r\n${html}`;
}

function buildRawEmail(msg: EmailMessage, signature: string): string {
    // Gmail API requires base64url-encoded RFC 2822 message
    return btoa(unescape(encodeURIComponent(composeRfc2822(msg, signature))))
        .replace(/\+/g, "-")
        .replace(/\//g, "_")
        .replace(/=+$/, "");
}

/**
 * Decoded, Slack-friendly rendering of the send body for dry-run display. Shows
 * the real envelope + HTML body but collapses the (often huge) send-as signature
 * to a length note — the real send includes it verbatim.
 */
function decodeForDisplay(msg: EmailMessage, signature: string, rawLength: number): string {
    const sigNote = signature
        ? `\u00AB signature omitted for display \u2014 ${signature.length.toLocaleString()} chars, sent verbatim \u00BB`
        : "(no signature)";
    return [
        `wire body: {"raw":"<base64url RFC-2822, ${rawLength.toLocaleString()} chars>"}`,
        "",
        "\u2014 decoded RFC-2822 \u2014",
        composeRfc2822(msg, sigNote),
    ].join("\n");
}

/**
 * Build (but do not send) the Gmail send request. Resolves the send-as
 * signature and auth token so the body and headers are exactly what will be
 * sent; performs no send. The body is `{ "raw": "<base64url RFC 2822>" }`.
 */
export async function buildSendEmailRequest(
    client: GoogleClient,
    msg: EmailMessage,
): Promise<PreparedRequest> {
    const signature = await fetchSignature(client, msg.sendAs.emailAddress);
    const raw = buildRawEmail(msg, signature);
    const headers = await client.getRequestHeaders();
    const body = JSON.stringify({ raw });
    return {
        label: `Gmail messages.send — to ${msg.to} (as ${msg.sendAs.emailAddress})`,
        method: "POST",
        url: `${BASE}/users/me/messages/send`,
        headers: { ...headers, "Content-Type": "application/json" },
        body,
        displayBody: decodeForDisplay(msg, signature, body.length),
    };
}

/** Send a prepared Gmail request. */
export async function executeSendEmail(
    req: PreparedRequest,
): Promise<{ ok: boolean; error?: string }> {
    try {
        log("executeSendEmail", req.label);
        const res = await fetch(req.url, {
            method: req.method,
            headers: req.headers,
            body: req.body,
        });
        if (!res.ok) {
            const text = await res.text();
            log("executeSendEmail", `failed (${res.status}): ${text}`);
            return { ok: false, error: `${res.status}: ${text}` };
        }
        const data = await res.json();
        log("executeSendEmail", `sent ok, messageId: ${data.id ?? "unknown"}`);
        return { ok: true };
    } catch (err) {
        const errMsg = err instanceof Error ? err.message : String(err);
        log("executeSendEmail", `failed: ${errMsg}`);
        return { ok: false, error: errMsg };
    }
}

export async function sendEmail(
    client: GoogleClient,
    msg: EmailMessage,
): Promise<{ ok: boolean; error?: string }> {
    try {
        const req = await buildSendEmailRequest(client, msg);
        return await executeSendEmail(req);
    } catch (err) {
        const errMsg = err instanceof Error ? err.message : String(err);
        log("sendEmail", `failed: ${errMsg}`);
        return { ok: false, error: errMsg };
    }
}
