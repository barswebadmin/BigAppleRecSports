/** Consolidated channel message posted after a real (non-dry-run) waitlist
 *  run. The workflow handles a single league at a time, so the league link,
 *  processor, sheet link, and remaining count appear once; each processed
 *  player is a bullet. */

import { section } from "../../shared/slack/blocks.ts";
import { type MessageBuilder } from "../../shared/slack/message.ts";
import { hyperlink, SLACK_LINK_TEXT, tagUser } from "../../shared/slack/mrkdwn.ts";
import { capitalize } from "../../shared/text/strings.ts";
import { formatDivision } from "../../domain/league/format.ts";
import type { ActionResult } from "../../domain/waitlist/action_result.ts";
import { formatActionBullet } from "./format.ts";

export interface WaitlistResultMessage {
    results: ActionResult[];
    processedBy?: string;
    remaining: number;
    sheetUrl: string;
}

const TITLE_PREFIX = "Waitlist updated";
const PROCESSED_BY_PREFIX = "Processed by";
const REMAINING_SUFFIX = "still on the waitlist";
const FALLBACK_LEAGUE_TEXT = "this league";
const META_SEPARATOR = "  ·  ";

// ============================================================================

// ============================================================================

export const buildWaitlistResultMessage: MessageBuilder<WaitlistResultMessage> = (input) => {
    const first = input.results[0];
    const lg = first?.league;
    const leagueText = lg
        ? `${capitalize(lg.day)} ${capitalize(lg.sport)} (${formatDivision(lg.division, "label")})`
        : FALLBACK_LEAGUE_TEXT;
    const leaguePart = first?.productUrl
        ? hyperlink(leagueText, first.productUrl)
        : `*${leagueText}*`;

    const metaParts: string[] = [];
    if (input.processedBy) metaParts.push(tagUser(input.processedBy, PROCESSED_BY_PREFIX));
    metaParts.push(`${Math.max(0, input.remaining)} ${REMAINING_SUFFIX}`);

    const headerLines = [
        `*${TITLE_PREFIX} — ${leaguePart}*`,
        metaParts.join(META_SEPARATOR),
        hyperlink(SLACK_LINK_TEXT.googleSheets, input.sheetUrl),
    ];
    const bulletLines = input.results.map((r) => `•  ${formatActionBullet(r)}`);

    return {
        text: [...headerLines, "", ...bulletLines].join("\n"),
        blocks: [section(headerLines.join("\n")), section(bulletLines.join("\n"))],
    };
};
