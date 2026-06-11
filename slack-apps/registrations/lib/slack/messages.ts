/**
 * Channel message assembly — generic over result type.
 */

export function buildActionMessage<T>(
    items: T[],
    formatSummary: (item: T) => string,
): { text: string; blocks: Record<string, unknown>[] } {
    const blocks: Record<string, unknown>[] = [];
    const textLines: string[] = [];

    for (let i = 0; i < items.length; i++) {
        const summary = formatSummary(items[i]);
        textLines.push(summary);
        if (i > 0) blocks.push({ type: "divider" });
        blocks.push({ type: "section", text: { type: "mrkdwn", text: summary } });
    }

    return { text: textLines.join("\n---\n"), blocks };
}
