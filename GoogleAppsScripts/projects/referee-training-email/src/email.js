// email.js — referee training confirmation email
//
// Self-contained: no shared-utilities import.
// Logo is fetched from Google Drive and attached inline as "barsLogo".

const BARS_LOGO_DRIVE_ID = '19v8HXXAz5a1m_rkiaUevpY0to97Q02E9';
const REPLY_TO = 'rich.marzullo@bigapplerecsports.com';

/**
 * Send a confirmation email to a registrant listing their confirmed training sessions.
 *
 * @param {object} params
 * @param {string}   params.to      - (required) Recipient email address
 * @param {string}   params.subject - (required) Email subject line
 * @param {string}   params.body    - (required) HTML body content
 */
export function sendConfirmationEmail({ to, subject, body }) {
  if (!subject) throw new Error('sendConfirmationEmail: subject is required');
  if (!body) throw new Error('sendConfirmationEmail: body is required');
  if (!to) throw new Error('sendConfirmationEmail: to is required');

  const logoBlob = DriveApp.getFileById(BARS_LOGO_DRIVE_ID).getBlob().setName('barsLogo');

  MailApp.sendEmail({
    to,
    subject,
    htmlBody: body,
    replyTo: REPLY_TO,
    inlineImages: { barsLogo: logoBlob },
  });
}
