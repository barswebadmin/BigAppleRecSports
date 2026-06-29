/**
 * Generic approval-modal block builder. Refund-agnostic — all domain labels,
 * action values, defaults, and amount/restock/notify configuration are passed
 * in by the caller. Refund-specific usage lives in
 * `views/refund/approve_modal.ts` as a thin caller of this builder.
 */

import {
  type Block,
  checkboxes,
  divider,
  input,
  radioButtons,
  toOption,
  toOptions,
} from "../../shared/slack/blocks.ts";
import { modal, type SlackView } from "../../shared/slack/message.ts";

/** Stable Slack block / action ids surfaced for caller use (the caller binds
 *  `views.update` and `view_submission` handlers against these). */
export const APPROVE_MODAL_ACTION_BLOCK_ID = "action_block";
export const APPROVE_MODAL_ACTION_ACTION_ID = "action_input";

export const APPROVE_MODAL_AMOUNT_BLOCK_ID = "amount_block";
export const APPROVE_MODAL_AMOUNT_ACTION_ID = "amount_input";

export const APPROVE_MODAL_RESTOCK_BLOCK_ID = "restock_block";
export const APPROVE_MODAL_RESTOCK_ACTION_ID = "restock_input";

export const APPROVE_MODAL_NOTIFY_BLOCK_ID = "notify_block";
export const APPROVE_MODAL_NOTIFY_ACTION_ID = "notify_input";

export interface ApproveModalActionOption {
  value: string;
  label: string;
}

export interface ApproveModalAmountInput {
  /** Initial amount value rendered in the input (caller formats to its preferred precision). */
  default: number;
  /** Soft-cap minimum (informational; surfaces in the hint copy). */
  min: number;
  /** Hard-cap maximum (informational; surfaces in the hint copy). */
  max: number;
  /** When `true`, Slack disables submit while the field is empty/invalid. */
  required: boolean;
  /** Optional helper copy rendered under the input. */
  hint?: string;
}

export interface ApproveModalNotifyToggle {
  /** Initial check state. */
  default: boolean;
  /** Visible label for the single checkbox option. */
  label: string;
  /** Option `value` round-tripped on submit. Default `"notify"`. */
  value?: string;
}

export interface ApproveModalArgs<TMeta extends Record<string, unknown>> {
  callbackId: string;
  title: string;
  submitLabel?: string;
  closeLabel?: string;
  /** Caller-built header (order summary, customer line, etc.). Rendered above
   *  the action radio. The builder adds a divider after this section. */
  headerBlocks: Block[];
  actionOptions: ApproveModalActionOption[];
  /** Initial action value. Defaults to the first option. */
  initialActionValue?: string;
  /** When set, renders the dollar-amount input. Omit for cancel-only flows. */
  amountInput?: ApproveModalAmountInput;
  /** When set, renders the restock radio group. Omit for refund-only flows. */
  restockOptions?: ApproveModalActionOption[];
  initialRestockValue?: string;
  /** When set, renders a single notify checkbox. Omit when notification is
   *  not configurable in this flow. */
  notifyToggle?: ApproveModalNotifyToggle;
  metadata: TMeta;
}

function actionRadioBlock(
  options: ApproveModalActionOption[],
  initial: string | undefined,
): Block {
  const opts = toOptions(
    options.map((o) => ({ label: o.label, value: o.value })),
  );
  const initialValue = initial ?? options[0]?.value;
  const initialOption = initialValue
    ? opts.find((o) => o.value === initialValue)
    : undefined;
  return input({
    blockId: APPROVE_MODAL_ACTION_BLOCK_ID,
    label: "Action",
    dispatchAction: true,
    element: radioButtons({
      actionId: APPROVE_MODAL_ACTION_ACTION_ID,
      options: opts,
      initial: initialOption,
    }),
  });
}

function amountBlock(amount: ApproveModalAmountInput): Block {
  return input({
    blockId: APPROVE_MODAL_AMOUNT_BLOCK_ID,
    label: "Amount (USD)",
    optional: !amount.required,
    hint: amount.hint,
    dispatchAction: true,
    element: {
      type: "plain_text_input",
      action_id: APPROVE_MODAL_AMOUNT_ACTION_ID,
      initial_value: amount.default.toFixed(2),
    },
  });
}

function restockBlock(
  options: ApproveModalActionOption[],
  initial: string | undefined,
): Block {
  const opts = toOptions(
    options.map((o) => ({ label: o.label, value: o.value })),
  );
  // Honor explicit undefined: caller passed no initial → no pre-selection.
  const initialOption = initial
    ? opts.find((o) => o.value === initial)
    : undefined;
  return input({
    blockId: APPROVE_MODAL_RESTOCK_BLOCK_ID,
    label: "Restock?",
    element: radioButtons({
      actionId: APPROVE_MODAL_RESTOCK_ACTION_ID,
      options: opts,
      initial: initialOption,
    }),
  });
}

function notifyBlock(toggle: ApproveModalNotifyToggle): Block {
  const opt = toOption({
    label: toggle.label,
    value: toggle.value ?? "notify",
  });
  return input({
    blockId: APPROVE_MODAL_NOTIFY_BLOCK_ID,
    label: "Notifications",
    optional: true,
    element: checkboxes({
      actionId: APPROVE_MODAL_NOTIFY_ACTION_ID,
      options: [opt],
      initial: toggle.default ? [opt] : undefined,
    }),
  });
}

/**
 * Build an approval-modal `SlackView`. Returns a view ready to splat into
 * `client.views.open` / `client.views.update`.
 */
export function approveModal<TMeta extends Record<string, unknown>>(
  args: ApproveModalArgs<TMeta>,
): SlackView {
  const blocks: Block[] = [];
  blocks.push(...args.headerBlocks);
  blocks.push(divider());
  blocks.push(actionRadioBlock(args.actionOptions, args.initialActionValue));
  if (args.amountInput) blocks.push(amountBlock(args.amountInput));
  if (args.restockOptions) {
    blocks.push(divider());
    blocks.push(restockBlock(args.restockOptions, args.initialRestockValue));
  }
  if (args.notifyToggle) {
    blocks.push(divider());
    blocks.push(notifyBlock(args.notifyToggle));
  }

  return modal({
    callbackId: args.callbackId,
    title: args.title,
    submitLabel: args.submitLabel ?? "Confirm & Process",
    closeLabel: args.closeLabel ?? "Cancel",
    blocks,
    metadata: JSON.stringify(args.metadata),
  });
}
