/**
 * Gmail API operations — raw fetch, no external dependencies.
 */

import type { GoogleClient } from "./client.ts";
import type { EmailMessage } from "./types/email_message.ts";

const BASE = "https://gmail.googleapis.com/gmail/v1";
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

function buildRawEmail(msg: EmailMessage, signature: string): string {
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

    // Gmail API requires base64url-encoded RFC 2822 message
    return btoa(unescape(encodeURIComponent(`${headers}\r\n\r\n${html}`)))
        .replace(/\+/g, "-")
        .replace(/\//g, "_")
        .replace(/=+$/, "");
}

export async function sendEmail(
    client: GoogleClient,
    msg: EmailMessage,
): Promise<{ ok: boolean; error?: string }> {
    try {
        const signature = await fetchSignature(client, msg.sendAs.emailAddress);
        const raw = buildRawEmail(msg, signature);

        log("sendEmail", `to="${msg.to}" subject="${msg.subject}"`);
        const reqHeaders = await client.getRequestHeaders();
        const res = await fetch(`${BASE}/users/me/messages/send`, {
            method: "POST",
            headers: { ...reqHeaders, "Content-Type": "application/json" },
            body: JSON.stringify({ raw }),
        });
        if (!res.ok) {
            const text = await res.text();
            log("sendEmail", `failed (${res.status}): ${text}`);
            return { ok: false, error: `${res.status}: ${text}` };
        }
        const data = await res.json();
        log("sendEmail", `sent ok, messageId: ${data.id ?? "unknown"}`);
        return { ok: true };
    } catch (err) {
        const errMsg = err instanceof Error ? err.message : String(err);
        log("sendEmail", `failed: ${errMsg}`);
        return { ok: false, error: errMsg };
    }
}
