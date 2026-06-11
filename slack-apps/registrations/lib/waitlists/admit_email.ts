/**
 * Waitlist admit email builders — pure string/config generation, no I/O.
 */

import type { League } from "../../types/league.ts";
import type { EmailMessage } from "../clients/google/types/email_message.ts";
import {
    buildLoginUrl,
    capitalize,
    formatDivision,
    formatProductHandle,
    formatSportLeadershipEmailAddress,
    formatSportLeadershipEmailSenderName,
} from "../../utils/formatters.ts";

const log = (fn: string, ...args: unknown[]) => console.log(`[email:${fn}]`, ...args);

export interface AdmitEmailRecipient {
    firstName: string;
    emailAddress: string;
}

export function buildSubject(league: League): string {
    const subject = `Big Apple ${capitalize(league.sport)} - A Spot Is Available for You`;
    log("buildSubject", { sport: league.sport, subject });
    return subject;
}

export function buildWaitlistAdmitEmailBody(firstName: string, league: League): string[] {
    log("buildWaitlistAdmitEmailBody", {
        firstName,
        league: `${league.sport}.${league.day}.${league.division}`,
    });
    const leagueLabel = `${capitalize(league.day)} ${capitalize(league.sport)} (${
        formatDivision(league.division)
    })`;
    const loginUrl = buildLoginUrl(formatProductHandle(league));
    const replyTo = formatSportLeadershipEmailAddress(league);

    return [
        `Hi ${capitalize(firstName)},`,
        `We are happy to inform you that a spot has opened up in <b>${leagueLabel}</b>, and you were next on the waitlist!`,
        `To register, please ensure you are signed into our site with the <b>same email address</b> you used to sign up for the waitlist (the one receiving this email). Sometimes Shopify auto-logins can use old email addresses, which has caused confusion. You <i>must</i> sign in <i>before</i> adding the registration product to your cart, otherwise you will not be able to register.`,
        `<a href="${loginUrl}">Here's a convenient login link</a> that takes you right to the registration page after login. In case it doesn't work (it <i>should</i>, but who ever knows), head to <a href="https://bigapplerecsports.com">bigapplerecsports.com</a>, log in at the top right, navigate to <b>Shop</b> &gt; <b>Registration</b> &gt; your sport/day, and register from there (laborious, we know).`,
        `Please let us know if you're no longer interested, so we can let the next person off the waitlist. If you have any questions, please reach out to <a href="mailto:${replyTo}">${replyTo}</a>.`,
    ];
}

export function buildWaitlistAdmitEmail(
    recipient: AdmitEmailRecipient,
    league: League,
): EmailMessage {
    log("buildWaitlistAdmitEmail", {
        to: recipient.emailAddress,
        firstName: recipient.firstName,
        league: `${league.sport}.${league.day}.${league.division}`,
    });
    return {
        to: recipient.emailAddress,
        subject: buildSubject(league),
        htmlBodyParts: buildWaitlistAdmitEmailBody(recipient.firstName, league),
        sendAs: {
            emailAddress: "web@bigapplerecsports.com",
            name: formatSportLeadershipEmailSenderName(league),
        },
        replyTo: formatSportLeadershipEmailAddress(league),
        cc: formatSportLeadershipEmailAddress(league),
    };
}
