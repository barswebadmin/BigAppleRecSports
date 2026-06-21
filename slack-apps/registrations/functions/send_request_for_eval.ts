/** Workflow boundary for the new sheet-driven refund-evaluation flow.
 *
 *  Slash command: `/eval-refund-request`. The flow:
 *    1. Operator runs the slash command.
 *    2. This function opens a picker modal listing every unprocessed row from
 *       the `Refund_Requests` Google Sheet.
 *    3. Operator picks a row + (optionally) toggles test mode + (optionally)
 *       overrides the post-to channel, then submits.
 *    4. The picker submission handler POSTs the picked row to
 *       `/refunds/validate` and pushes the refund-approval modal pre-filled
 *       with the validated estimate.
 *    5. The approval-modal submission handler POSTs to `/refunds/create`
 *       and posts the result card to the resolved channel.
 */

import { DefineFunction, Schema, SlackFunction } from "deno-slack-sdk/mod.ts";

import { makeBarsApiClient } from "../clients/bars_api/client.ts";
import { fetchRefundRequestsOrEmpty } from "../domain/refund/sheet_loader.ts";
import { normalizeRefundOrCredit } from "../domain/refund/normalizers.ts";
import type {
  CreateRefundRequest,
  CreateRefundResponse,
  RefundDecision,
  RefundRequestEval,
  RefundSheetData,
  RefundSheetEntry,
  RefundTo,
  ValidateRefundRequest,
} from "../domain/refund/types.ts";
import {
  PICKER_ENTRIES_PER_PAGE_DEFAULT,
  pickerActionIds,
  pickerModal,
} from "../views/_shared/picker_modal.ts";
import {
  type ApproveModalMeta,
  buildApproveModal,
  extractApproveModalValues,
  REFUND_APPROVAL_MODAL_CALLBACK_ID,
} from "../views/refund/approve_modal.ts";
import { buildRefundResultBlocks } from "../views/refund/eval_blocks.ts";
import { type Block, input, toOption } from "../shared/slack/blocks.ts";
import { extractModalState } from "../shared/slack/modal_state.ts";
import {
  completeWithEmpty,
  makeWorkflowCompleter,
} from "../shared/slack/workflow.ts";
import { resolveRefundChannel } from "../shared/slack/channel.ts";

// ────────────────────────────────────────────────────────────────────────────
// Per-flow constants (live alongside the calling function — these are NOT
// generic picker primitives, they belong to THIS flow only)
// ────────────────────────────────────────────────────────────────────────────

export const PICK_ROW_CALLBACK_ID = "refund_pick_row";

/** Action id for the test-mode toggle checkbox (built as `extraInputBlocks`
 *  for the picker modal). */
export const ACTION_TOGGLE_TEST_MODE = "refund_toggle_test";

/** Block / action ids for the "post review card to channel" plain-text input. */
export const BLOCK_POST_TO_CHANNEL = "refund_post_to_channel";
export const ACTION_POST_TO_CHANNEL = "refund_post_to_channel_input";

const TEST_MODE_OPTION = {
  label: "Run in test mode (no live Shopify writes)",
  value: "test",
};

/** Persisted modal state (private_metadata). */
export interface PickRowModalState {
  /** Pagination offset into the unprocessed-rows list. */
  off: number;
  /** Single-select — the rowNumber of the picked entry, or null when unset. */
  selectedRowNumber: number | null;
  /** Whether the test-mode checkbox is ticked. */
  isTest: boolean;
  /** Channel the slash command was invoked from (default for "post to"). */
  ch: string;
  /** Operator-overridden post-target; round-trips into ApproveModalMeta on
   *  submit so the final-message chat.postMessage lands in the same channel
   *  that received the review card. Falls back to the env default → "#joe-test"
   *  when null/empty (see resolveRefundChannel). */
  slackChannel: string | null;
}

const log = (fn: string, ...args: unknown[]) =>
  console.log(`[send_request_for_eval:${fn}]`, ...args);

// ────────────────────────────────────────────────────────────────────────────
// Modal builders
// ────────────────────────────────────────────────────────────────────────────

function formatEntry(entry: RefundSheetEntry): {
  title: string;
  context?: string[];
} {
  const name =
    `${entry.firstName} ${entry.lastName}`.trim() || `Row ${entry.rowNumber}`;
  const orderRef = entry.orderNumber ? `#${entry.orderNumber}` : "(no order #)";
  return {
    title: `${name} • ${orderRef}`,
    context: [entry.timestamp || "(no timestamp)"],
  };
}

function buildExtraInputBlocks(state: PickRowModalState): Block[] {
  const testOpt = toOption(TEST_MODE_OPTION);
  const blocks: Block[] = [
    {
      type: "actions",
      block_id: `${ACTION_TOGGLE_TEST_MODE}_block`,
      elements: [
        {
          type: "checkboxes",
          action_id: ACTION_TOGGLE_TEST_MODE,
          options: [testOpt],
          ...(state.isTest ? { initial_options: [testOpt] } : {}),
        },
      ],
    },
    input({
      blockId: BLOCK_POST_TO_CHANNEL,
      label: "Post review card to channel",
      optional: true,
      hint: "Channel id (e.g. C12345) or name (#joe-test). Leave blank to use the default refund channel.",
      element: {
        type: "plain_text_input",
        action_id: ACTION_POST_TO_CHANNEL,
        initial_value: state.slackChannel ?? state.ch ?? "",
      },
    }),
  ];
  return blocks;
}

function buildPickerView(sheet: RefundSheetData, state: PickRowModalState) {
  return pickerModal<RefundSheetEntry>({
    callbackId: PICK_ROW_CALLBACK_ID,
    title: "Evaluate Refund Request",
    submitLabel: "Evaluate",
    closeLabel: "Cancel",
    items: sheet.unprocessed,
    formatItem: formatEntry,
    getItemId: (e) => e.rowNumber,
    pageSize: PICKER_ENTRIES_PER_PAGE_DEFAULT,
    currentOffset: state.off,
    selectedItemId: state.selectedRowNumber,
    extraInputBlocks: buildExtraInputBlocks(state),
    metadata: state as unknown as Record<string, unknown>,
    emptyMessage:
      "No unprocessed refund requests found. Add new rows to the sheet (or clear a Status cell) and try again.",
  });
}

// ────────────────────────────────────────────────────────────────────────────
// State capture helpers
// ────────────────────────────────────────────────────────────────────────────

// deno-lint-ignore no-explicit-any
type SlackBody = any;

function readPostToChannel(body: SlackBody): string | null {
  const v =
    body.view?.state?.values?.[BLOCK_POST_TO_CHANNEL]?.[ACTION_POST_TO_CHANNEL]
      ?.value;
  if (typeof v === "string" && v.trim() !== "") return v.trim();
  return null;
}

function readIsTest(body: SlackBody): boolean {
  const block = body.view?.state?.values?.[`${ACTION_TOGGLE_TEST_MODE}_block`];
  const action = block?.[ACTION_TOGGLE_TEST_MODE];
  const opts = action?.selected_options as { value: string }[] | undefined;
  return (
    Array.isArray(opts) && opts.some((o) => o.value === TEST_MODE_OPTION.value)
  );
}

function readSelectedRow(
  body: SlackBody,
  state: PickRowModalState,
): number | null {
  // Radios live under a per-page block id minted by pickerModal. Walk every
  // block in view.state.values and pick up any radio whose action id starts
  // with the radio prefix.
  const ids = pickerActionIds(PICK_ROW_CALLBACK_ID);
  const values = body.view?.state?.values ?? {};
  for (const block of Object.values<
    Record<string, { selected_option?: { value: string } }>
  >(values)) {
    for (const [actionId, action] of Object.entries(block)) {
      if (actionId.startsWith(ids.radioPrefix)) {
        const v = action.selected_option?.value;
        if (v !== undefined && v !== "") {
          const n = Number.parseInt(v, 10);
          if (Number.isFinite(n)) return n;
        }
      }
    }
  }
  return state.selectedRowNumber;
}

function captureState(body: SlackBody): PickRowModalState {
  const persisted = extractModalState<PickRowModalState>(body);
  const next: PickRowModalState = {
    off: persisted.off ?? 0,
    selectedRowNumber: persisted.selectedRowNumber ?? null,
    isTest: persisted.isTest ?? false,
    ch: persisted.ch ?? "",
    slackChannel: persisted.slackChannel ?? null,
  };
  // Fold in fresh page state.
  next.selectedRowNumber = readSelectedRow(body, next);
  next.isTest = readIsTest(body);
  const overrideCh = readPostToChannel(body);
  if (overrideCh !== null) next.slackChannel = overrideCh;
  return next;
}

// ────────────────────────────────────────────────────────────────────────────
// SlackFunction definition + handler wiring
// ────────────────────────────────────────────────────────────────────────────

export const SendRequestForEvalFunction = DefineFunction({
  callback_id: "send_request_for_eval",
  title: "Pick a refund request to evaluate",
  source_file: "functions/send_request_for_eval.ts",
  input_parameters: {
    properties: {
      interactivity: { type: Schema.slack.types.interactivity },
      channel_id: { type: Schema.slack.types.channel_id },
      slack_channel: { type: Schema.types.string },
    },
    required: ["interactivity", "channel_id"],
  },
  output_parameters: {
    properties: {
      processed_row_number: { type: Schema.types.string },
    },
    required: [],
  },
});

const handler = SlackFunction(
  SendRequestForEvalFunction,
  async ({ inputs, client, env }) => {
    const sheet = await fetchRefundRequestsOrEmpty(env);

    const state: PickRowModalState = {
      off: 0,
      selectedRowNumber: null,
      isTest: false,
      ch: inputs.channel_id,
      slackChannel: inputs.slack_channel?.trim()
        ? inputs.slack_channel.trim()
        : null,
    };

    const openRes = await client.views.open({
      interactivity_pointer: inputs.interactivity.interactivity_pointer,
      view: buildPickerView(sheet, state),
    });
    if (!openRes.ok) {
      return { error: `Failed to open picker modal: ${openRes.error}` };
    }

    return { completed: false };
  },
);

// Pagination — fold the visible page's selection into state, advance the
// offset, and re-render in place.
handler.addBlockActionsHandler(
  new RegExp(`^${PICK_ROW_CALLBACK_ID}__(?:next|prev)_page$`),
  async ({ action, body, client, env }) => {
    const state = captureState(body);
    const ids = pickerActionIds(PICK_ROW_CALLBACK_ID);
    const pageSize = PICKER_ENTRIES_PER_PAGE_DEFAULT;
    if (action.action_id === ids.nextPage) {
      state.off = state.off + pageSize;
    } else if (action.action_id === ids.prevPage) {
      state.off = Math.max(0, state.off - pageSize);
    }
    const sheet = await fetchRefundRequestsOrEmpty(env);
    await client.views.update({
      view_id: body.view?.id,
      view: buildPickerView(sheet, state),
    });
  },
);

// Radio selection / checkbox toggle — capture state but no view.update is
// needed (Slack handles the radio + checkbox UI in-place). Ack with no-op.
handler.addBlockActionsHandler(
  new RegExp(`^${PICK_ROW_CALLBACK_ID}__radio_\\d+$`),
  () => {},
);
handler.addBlockActionsHandler(ACTION_TOGGLE_TEST_MODE, () => {});

// Submission — capture final state, look up the picked row, POST it to
// `/refunds/validate`, and push the approval modal pre-filled with the
// estimate. On validate failure, post an error message and complete the
// workflow cleanly. The approval modal's submission handler (below) handles
// the `/refunds/create` round-trip and final result posting.
handler.addViewSubmissionHandler(
  PICK_ROW_CALLBACK_ID,
  async ({ body, client, env }) => {
    const state = captureState(body);
    if (state.selectedRowNumber === null) {
      log("submit", "no row selected — completing with no action");
      await completeWithEmpty(client, body);
      return;
    }

    const sheet = await fetchRefundRequestsOrEmpty(env);
    const picked = sheet.unprocessed.find(
      (e) => e.rowNumber === state.selectedRowNumber,
    );
    if (!picked) {
      log(
        "submit",
        `selected row ${state.selectedRowNumber} no longer present`,
      );
      await completeWithEmpty(client, body);
      return;
    }

    const channel = resolveRefundChannel({
      requested: state.slackChannel,
      env,
    });
    const refundTo: RefundTo = normalizeRefundOrCredit(picked.refundOrCredit);

    const validateBody: ValidateRefundRequest = {
      orderNumber: picked.orderNumber,
      requestedRefundTo: refundTo,
      requesterEmail: picked.email,
      requesterFirstName: picked.firstName,
      requesterLastName: picked.lastName,
      notes: picked.notes,
      transferRequest: picked.transferRequest,
      sheetRowRef: {
        spreadsheetId: sheet.spreadsheetId,
        tabId: sheet.tabId,
        rowNumber: picked.rowNumber,
      },
      ...(state.isTest ? { isTest: true } : {}),
    };

    log("submit", {
      rowNumber: picked.rowNumber,
      orderNumber: picked.orderNumber,
      channel,
      isTest: state.isTest,
    });

    let refundEval: RefundRequestEval;
    try {
      const barsApi = makeBarsApiClient(env);
      refundEval = await barsApi.post<RefundRequestEval>({
        endpoint: "/refunds/validate",
        body: validateBody,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      log("submit", `validate failed: ${message}`);
      await client.chat.postMessage({
        channel,
        text: `Refund validation failed: ${message}`,
        blocks: [
          {
            type: "context",
            elements: [
              {
                type: "mrkdwn",
                text: `:x: Refund validation failed for row ${picked.rowNumber}: ${message}`,
              },
            ],
          },
        ],
      });
      await completeWithEmpty(client, body);
      return;
    }

    // The sheet-driven flow has no pre-existing review-card message to
    // chat.update; the eval card IS the approval modal itself, and the
    // result card is posted fresh on submit. `message_ts` is empty by
    // design.
    const approveMeta: ApproveModalMeta & Record<string, unknown> = {
      channel,
      message_ts: "",
      orderId: refundEval.order.id,
      productId: refundEval.product.id,
      refundTo,
      refundEval,
    };

    const approveView = buildApproveModal({
      orderNumber: refundEval.order.number,
      refundable: refundEval.order.amountPaid,
      totalPaid: refundEval.order.amountPaid,
      estimatedOriginal: refundEval.estimate.original.amount,
      estimatedCredit: refundEval.estimate.storeCredit.amount,
      refundTo,
      action: "cancel_refund",
      currentAmount: refundEval.estimate.original.amount.toFixed(2),
      restock: undefined,
      // TODO: real privilege check — the modal submit handler currently
      // always posts /refunds/create when the operator confirms.
      isPrivileged: true,
      meta: approveMeta,
    });

    return {
      response_action: "push",
      view: approveView,
    };
  },
);

// Closing the modal (Cancel/Close) must still complete the workflow step.
handler.addViewClosedHandler(PICK_ROW_CALLBACK_ID, async ({ body, client }) => {
  await completeWithEmpty(client, body);
});

// ────────────────────────────────────────────────────────────────────────────
// Approval modal (pushed on top of the picker after /refunds/validate)
// ────────────────────────────────────────────────────────────────────────────

interface ApproveModalRoundTrip extends ApproveModalMeta {
  orderId: string;
  productId: string;
  refundTo: RefundTo;
  refundEval: RefundRequestEval;
}

handler.addViewSubmissionHandler(
  REFUND_APPROVAL_MODAL_CALLBACK_ID,
  async ({ body, view, client, env }) => {
    const meta = JSON.parse(
      view.private_metadata || "{}",
    ) as ApproveModalRoundTrip;
    const values = extractApproveModalValues(view.state?.values ?? {});

    const createBody: CreateRefundRequest = {
      orderId: meta.orderId,
      productId: meta.productId,
      refundTo: meta.refundTo,
      amount: values.amount,
      cancel:
        values.action === "cancel_only" || values.action === "cancel_refund",
      refund:
        values.action === "refund_only" || values.action === "cancel_refund",
      ...(values.restock ? { restockTo: values.restock } : {}),
      notify: values.sendNotification,
      approvedBy: body.user.id,
      isTest: false,
    };

    try {
      const barsApi = makeBarsApiClient(env);
      const result = await barsApi.post<CreateRefundResponse>({
        endpoint: "/refunds/create",
        body: createBody,
      });

      const decision: RefundDecision = {
        status: "approved",
        by: body.user.id,
        amount: values.amount ?? undefined,
        refundType: meta.refundTo,
        approveAction: values.action,
        restock: values.restock,
        sendNotification: values.sendNotification,
      };
      const finalBlocks = buildRefundResultBlocks(result, decision);
      await client.chat.postMessage({
        channel: meta.channel,
        text: `Refund result for ${meta.refundTo}`,
        blocks: finalBlocks,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      log("approve_submit", `create failed: ${message}`);
      await client.chat.postMessage({
        channel: meta.channel,
        text: `Refund execution failed: ${message}`,
        blocks: [
          {
            type: "context",
            elements: [
              {
                type: "mrkdwn",
                text: `:x: Refund execution failed: ${message}`,
              },
            ],
          },
        ],
      });
    }

    const complete = makeWorkflowCompleter(client, body);
    await complete(JSON.stringify({ orderId: meta.orderId }));
  },
);

handler.addViewClosedHandler(
  REFUND_APPROVAL_MODAL_CALLBACK_ID,
  async ({ body, client }) => {
    await completeWithEmpty(client, body);
  },
);

export default handler;
