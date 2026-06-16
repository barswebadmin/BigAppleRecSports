export type Block = Record<string, unknown>;

export function plainText(text: string, emoji = false) {
    return {
        type: "plain_text" as const,
        text,
        ...(emoji ? { emoji: true } : {}),
    };
}

export function section(text: string): Block {
    return { type: "section", text: { type: "mrkdwn", text } };
}

export function header(text: string): Block {
    return {
        type: "header",
        text: { type: "plain_text", text: text.slice(0, 150), emoji: true },
    };
}

export function divider(): Block {
    return { type: "divider" };
}

export function context(text: string): Block {
    return {
        type: "context",
        elements: [{ type: "mrkdwn", text }],
    };
}
