/**
 * Block Kit `button` elements via slack-block-builder.
 * `value` (in-app action payload) xor `url` (opens link).
 */

import { Button } from "slack-block-builder";
import type { Block } from "./blocks.ts";

export type BlockKitButtonConfig =
    | { actionId: string; label: string; style?: "primary" | "danger"; value: string }
    | { actionId: string; label: string; style?: "primary" | "danger"; url: string };

export function blockKitButton(config: BlockKitButtonConfig): Block {
    let el = Button().text(config.label).actionId(config.actionId);
    el = "url" in config ? el.url(config.url) : el.value(config.value);
    if (config.style === "primary") el = el.primary();
    if (config.style === "danger") el = el.danger();
    return (el as unknown as { build(): Block }).build();
}
