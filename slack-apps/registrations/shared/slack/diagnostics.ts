import type { SlackMessage } from "./message.ts";
import { type Block, context, section } from "./blocks.ts";

const EMOJI = {
    success: ":white_check_mark:",
    warn: ":warning:",
    error: ":x:",
} as const;

export function formatDiagnostic(
    level: "success" | "warn" | "error",
    summary: string,
    details?: string,
): SlackMessage {
    const emoji = EMOJI[level];
    const text = `${emoji} ${summary}`;
    const blocks: Block[] = [section(`${emoji} *${summary}*`)];
    if (details) blocks.push(context(details));
    return { text, blocks };
}
