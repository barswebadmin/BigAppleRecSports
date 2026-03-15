// sendVeteranEmail.js — veteran eligibility notification email

import { sendBarsEmail } from '../../../shared-utilities/emailUtils.js';

const required = (name) => { throw new Error(`sendVeteranEmail: "${name}" is required`); };

/**
 * Send veteran eligibility emails to a list of players in BCC batches.
 *
 * @param {object} params
 * @param {string[]} params.veteransList          - (required) Array of recipient email addresses
 * @param {string}   params.sport                 - (required) Sport name (e.g. "Kickball")
 * @param {string}   params.day                   - (required) Day of week (e.g. "Saturday")
 * @param {string}   params.division              - (required) Division name
 * @param {string}   params.season                - (required) Season name (e.g. "Spring")
 * @param {string}   params.year                  - (required) Year (e.g. "2026")
 * @param {string}   params.leadershipEmailAddress - (required) Leadership email for replyTo and cc on last batch
 */
export function sendVeteranEmail({
  veteransList = required('veteransList'),
  sport = required('sport'),
  day = required('day'),
  division = required('division'),
  season = required('season'),
  year = required('year'),
  leadershipEmailAddress = required('leadershipEmailAddress'),
}) {
  const subject = `Big Apple ${sport} - Veteran Eligibility for: ${season} ${year} - ${day} - ${division} Division`;

  const body = `
    <p>Hello!</p>
    <p>You are receiving this email because you met the attendance requirements to register as a veteran
    for the <b>${season} ${year} season of ${sport} - ${day} - ${division} Division</b>.
    In order to register during the veteran registration window, you <i>must</i>
    <a href='https://shopify.com/55475535966/account?locale=en&region_country=US' target='_blank'>Sign In to the BARS website</a>
    using this email address (you will typically get a code emailed or texted to you and use that to validate your sign in)
    — if you don't, you will not be able to add the Registration product to your cart.
    (If you haven't before, we recommend signing in <i>before</i> your registration period starts in case you have any trouble;
    we may not be able to help right at registration time.)</p>

    <p>Please note that veteran status does not guarantee your registration — you must register successfully
    during the Veteran Registration window in order to secure your spot.</p>

    <p>If you have any questions, please reach out to
    <a style='color:blue' href='mailto:${leadershipEmailAddress}'>${leadershipEmailAddress}</a></p>

    --<br>
    <p>Warmly,<br>
    <b>BARS Leadership</b></p>
    <img src="cid:barsLogo" style="width:225px; height:auto;">
  `;

  sendBarsEmail({
    subject,
    htmlBody: body,
    bcc: veteransList,
    cc: leadershipEmailAddress,
    replyTo: leadershipEmailAddress,
    senderName: 'BARS Web Admin',
    batchSize: 45,
  });
}
