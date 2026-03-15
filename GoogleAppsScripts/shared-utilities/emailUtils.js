// emailUtils.js — shared BARS email utility
//
// Usage in any esbuild project:
//   import { sendBarsEmail } from '../../../shared-utilities/emailUtils.js';

// Logo registry — keys are human-readable aliases, values are Google Drive file IDs.
// Add new logos here; pass the key as `logo` to sendBarsEmail.
const LOGOS = {
  '2026_fullcolor_light': '19v8HXXAz5a1m_rkiaUevpY0to97Q02E9',
  // '2026_fullcolor_dark': '<drive-file-id>',
};

/**
 * Normalize a recipient field to a clean comma-separated string.
 * Accepts a string (comma-separated) or an array of strings.
 * Trims whitespace from each address.
 *
 * @param {string|string[]|null} value
 * @returns {string|null}
 */
function normalizeRecipients(value) {
  if (!value) return null;
  const arr = Array.isArray(value) ? value : value.split(',');
  const cleaned = arr.map((s) => s.trim()).filter(Boolean);
  return cleaned.length ? cleaned.join(',') : null;
}

/**
 * Send a BARS-branded email with optional inline logo.
 *
 * At least one of `to` or `bcc` is required.
 * When `batchSize` is set, `bcc` is split into chunks and one email is sent per batch.
 * The last batch automatically adds `cc` if provided.
 *
 * To embed the logo in your HTML body, use: <img src="cid:barsLogo" style="width:225px;">
 *
 * @param {object} params
 * @param {string}            params.subject                        - (required) Email subject line
 * @param {string}            params.htmlBody                       - (required) HTML body content
 * @param {string|string[]}  [params.to=null]                      - Recipient(s)
 * @param {string|string[]}  [params.cc=null]                      - CC recipient(s)
 * @param {string|string[]}  [params.bcc=null]                     - BCC recipient(s)
 * @param {string}           [params.replyTo=null]                  - Reply-to address
 * @param {string}           [params.senderName='BARS Web Admin']   - Display name shown in recipient's inbox (not the sending address)
 * @param {string|null}      [params.logo='2026_fullcolor_light']   - Logo key from LOGOS registry, or null to omit
 * @param {number|null}      [params.batchSize=null]                - Split bcc into batches of this size; null = single send
 */
export function sendBarsEmail({
  subject,
  htmlBody,
  to = null,
  cc = null,
  bcc = null,
  replyTo = null,
  senderName = 'BARS Web Admin',
  logo = '2026_fullcolor_light',
  batchSize = null,
}) {
  if (!subject) throw new Error('sendBarsEmail: subject is required');
  if (!htmlBody) throw new Error('sendBarsEmail: htmlBody is required');
  if (!to && !bcc) throw new Error('sendBarsEmail: at least one of to or bcc is required');

  // Resolve logo blob once (shared across all batches)
  let inlineImages = undefined;
  if (logo) {
    const fileId = LOGOS[logo];
    if (!fileId) throw new Error(`sendBarsEmail: unknown logo key "${logo}". Available: ${Object.keys(LOGOS).join(', ')}`);
    const blob = DriveApp.getFileById(fileId).getBlob().setName('barsLogo');
    inlineImages = { barsLogo: blob };
  }

  const normalizedTo = normalizeRecipients(to);
  const normalizedCc = normalizeRecipients(cc);
  const bccList = bcc
    ? (Array.isArray(bcc) ? bcc.map((s) => s.trim()).filter(Boolean) : bcc.split(',').map((s) => s.trim()).filter(Boolean))
    : [];

  // Base options shared across all sends
  const baseOptions = {
    subject,
    htmlBody,
    name: senderName,
    ...(replyTo && { replyTo }),
    ...(inlineImages && { inlineImages }),
  };

  if (!batchSize || bccList.length === 0) {
    // Single send
    MailApp.sendEmail({
      ...baseOptions,
      ...(normalizedTo && { to: normalizedTo }),
      ...(normalizedCc && { cc: normalizedCc }),
      ...(bccList.length && { bcc: bccList.join(',') }),
    });
    return;
  }

  // Batched BCC send
  for (let i = 0; i < bccList.length; i += batchSize) {
    const chunk = bccList.slice(i, i + batchSize);
    const isLast = i + batchSize >= bccList.length;

    MailApp.sendEmail({
      ...baseOptions,
      to: normalizedTo || 'undisclosed-recipients:;',
      bcc: chunk.join(','),
      ...(isLast && normalizedCc && { cc: normalizedCc }),
    });
  }
}
