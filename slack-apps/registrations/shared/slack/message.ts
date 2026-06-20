/** Common Slack-message and Slack-view shapes + builder type aliases.
 *
 *  Every channel post the app produces is a `SlackMessage` (`{ text, blocks }`)
 *  and every modal it opens is a `SlackView`. Domain modules define a named
 *  input type per message/view kind (e.g. `WaitlistResultMessage`,
 *  `WaitlistConfirmModal`) and expose a `MessageBuilder<T>` / `ViewBuilder<T>`
 *  free function. Caller pattern: `buildSomeMessage(input)` returning the
 *  common shape, ready to splat into `client.chat.postMessage` /
 *  `client.views.open`. */

import { type Block, plainText } from "./blocks.ts";

export interface SlackMessage {
    text: string;
    blocks: Block[];
}

interface PlainText {
    type: "plain_text";
    text: string;
    emoji?: boolean;
}

export interface SlackView {
    type: "modal";
    callback_id: string;
    private_metadata?: string;
    title: PlainText;
    submit?: PlainText;
    close?: PlainText;
    blocks: Block[];
    notify_on_close?: boolean;
}

export type MessageBuilder<TInput> = (input: TInput) => SlackMessage;
export type ViewBuilder<TInput> = (input: TInput) => SlackView;

/** Compose a `SlackView` from its semantic parts. Domain builders pass in
 *  what's in the modal; the Block Kit shell shape (type, title/submit/close
 *  as plain_text, optional private_metadata) lives in one place. */
export function modal(args: {
    callbackId: string;
    title: string;
    blocks: Block[];
    submitLabel?: string;
    closeLabel?: string;
    metadata?: string;
    notifyOnClose?: boolean;
}): SlackView {
    return {
        type: "modal",
        callback_id: args.callbackId,
        title: plainText(args.title),
        ...(args.submitLabel ? { submit: plainText(args.submitLabel) } : {}),
        ...(args.closeLabel ? { close: plainText(args.closeLabel) } : {}),
        blocks: args.blocks,
        ...(args.metadata ? { private_metadata: args.metadata } : {}),
        ...(args.notifyOnClose ? { notify_on_close: true } : {}),
    };
}
