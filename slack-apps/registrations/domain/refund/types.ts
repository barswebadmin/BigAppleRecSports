/**
 * Refund-domain types. Two layers of types live here:
 *
 *   1. Slack-side domain objects for the sheet-driven `/eval-refund-request`
 *      flow (sheet rows, sheet snapshot, reviewer decision).
 *
 *   2. Wire-shape types for the BARS API `/refunds/validate` and
 *      `/refunds/create` endpoints. These mirror the camelCase JSON the
 *      backend emits/accepts. They have no transport dependency — the
 *      domain-agnostic HTTP wrapper (`clients/bars_api/client.ts`) is
 *      called by parameterizing it with these inputs at the call site.
 *
 * Wire-shape sources of truth (per design.md):
 *   - `ValidateRefundRequest` ↔ POST /refunds/validate body
 *   - `RefundRequestEval` ↔ POST /refunds/validate response (plain dict on
 *     the backend; this Slack-side interface mirrors the camelCase wire JSON)
 *   - `CreateRefundRequest` ↔ POST /refunds/create body
 *   - `CreateRefundResponse` ↔ POST /refunds/create response
 */

// ════════════════════════════════════════════════════════════════════════════
// Sheet-driven /eval-refund-request flow — domain objects
// ════════════════════════════════════════════════════════════════════════════

/** Canonical refund-target enum. */
export type RefundTo = "original_method" | "store_credit";

/** One unprocessed entry parsed from the `Refund_Requests` sheet's data area.
 *
 *  No `policyConfirmation` field — the loader does NOT capture the "refund
 *  policy" column. The form gates submission on it but no consumer requires
 *  it; per design we ignore it. */
export interface RefundSheetEntry {
  /** 1-based row number in the sheet (header is row 1). */
  rowNumber: number;
  /** Raw "Timestamp" cell. */
  timestamp: string;
  email: string;
  firstName: string;
  lastName: string;
  /** Normalized — leading "#" stripped. */
  orderNumber: string;
  /** RAW cell value (e.g. "Store credit for a future order") from the
   *  "store credit" / "original form" / "refund" substring column.
   *  Normalization to `RefundTo` happens via
   *  `domain/refund/normalizers.ts#normalizeRefundOrCredit` before the
   *  validate request body is built — NOT here. The sheet entry stays
   *  faithful to the spreadsheet so unexpected answer strings are visible
   *  in logs. */
  refundOrCredit: string | null;
  /** Resolved from the "anything else" / "note about" substring column. */
  notes: string | null;
  /** OPTIONAL — resolved from the "transfer to another day" / "sport, day,
   *  and division" substring column. No consumer requires it; round-tripped
   *  to the backend on the validate request body for diagnostic logging. */
  transferRequest: string | null;
  /** Raw value of the Status cell, or null if the column is absent.
   *  Unprocessed predicate is inlined at every call site as
   *  `!!row.statusCellValue?.trim()` — no helper function. */
  statusCellValue: string | null;
  /** Derived: `!!statusCellValue?.trim()`. */
  isProcessed: boolean;
}

/** Sheet snapshot returned by `fetchRefundRequests(env)`. Diagnostic fields
 *  are intentionally absent — operator UX is "the row appears or it doesn't"
 *  (D25). */
export interface RefundSheetData {
  /** Deep-link to the tab. */
  url: string;
  spreadsheetId: string;
  tabId: string;
  /** Rows where `isProcessed === false`. */
  unprocessed: RefundSheetEntry[];
}

/** Final reviewer decision; consumed by the eval card view to render a status
 *  line and drop the action buttons. Pure data — UI mapping lives in views/. */
export interface RefundDecision {
  status: "approved" | "denied";
  by: string; // Slack user id
  amount?: number;
  refundType?: string;
  /** True when the approval only previewed payloads (didn't post a live
   *  /refunds/create request). */
  dryRun?: boolean;
  /** Modal action: cancel_refund | cancel_only | refund_only. */
  approveAction?: string;
  restock?: string;
  sendNotification?: boolean;
}

// ════════════════════════════════════════════════════════════════════════════
// BARS API wire shapes — POST /refunds/validate
// ════════════════════════════════════════════════════════════════════════════

export interface ValidateRefundSheetRowRef {
  spreadsheetId: string;
  tabId: string;
  rowNumber: number;
}

export interface ValidateRefundRequest {
  orderNumber: string;
  requestedRefundTo: RefundTo;
  /** REQUIRED — the requester's email from the sheet row. */
  requesterEmail: string;
  /** REQUIRED. */
  requesterFirstName: string;
  /** REQUIRED. */
  requesterLastName: string;
  /** OPTIONAL. */
  notes?: string | null;
  /** OPTIONAL — round-trips the sheet's "transfer to another day" cell for
   *  diagnostic logging on the backend. No consumer requires it. */
  transferRequest?: string | null;
  /** OPTIONAL. */
  sheetRowRef?: ValidateRefundSheetRowRef;
  /** OPTIONAL — defaults to false on the backend. Slack handler omits when
   *  not in test mode. */
  isTest?: boolean;
}

/** Per-tier estimate output. */
export interface TierEstimate {
  amount: number;
  percentage: number;
  tierLabel: string;
  appliedProcessingFee: number;
  notes: string[];
}

/** Order summary block embedded in the validate response. */
export interface RefundEvalOrder {
  /** Shopify order GID. */
  id: string;
  number: string;
  customerName: string;
  /** The order's customer email. */
  email: string;
  /** Total paid on the order, in dollars. */
  amountPaid: number;
  currency: string;
}

/** Product summary block embedded in the validate response. */
export interface RefundEvalProduct {
  /** Shopify product GID. */
  id: string;
  /** Canonical product URL. */
  url: string;
  year: number;
  /** "Winter" | "Spring" | "Summer" | "Fall". */
  season: string;
  sport: string;
  day: string;
  /** "WTNB+" | "Open" | … */
  division: string;
  /** ISO date — first session. Null when unparseable. */
  week1Start: string | null;
  week2Start: string | null;
  week3Start: string | null;
  week4Start: string | null;
  week5Start: string | null;
}

export interface RefundEvalEstimate {
  original: TierEstimate;
  storeCredit: TierEstimate;
}

export interface RefundRequestEval {
  ok: boolean;
  /** Replaces `validation.matched`. */
  isValid: boolean;
  /** Replaces `validation.mismatches[]`; flat string[] only. Absent on the
   *  happy path; populated when `isValid` is false. */
  validationErrors?: string[] | null;
  order: RefundEvalOrder;
  product: RefundEvalProduct;
  estimate: RefundEvalEstimate;
}

// ════════════════════════════════════════════════════════════════════════════
// BARS API wire shapes — POST /refunds/create
// ════════════════════════════════════════════════════════════════════════════

/** Restock destination for the line item being refunded. Omit the field
 *  entirely when no restock is intended — there is no "none" sentinel. */
export type RefundRestockTo =
  | "veteran"
  | "early"
  | "general"
  | "waitlist"
  | "full";

export interface CreateRefundRequest {
  /** REQUIRED — round-tripped from /validate. */
  orderId: string;
  /** REQUIRED — round-tripped from /validate. */
  productId: string;
  refundTo: RefundTo;
  /** REQUIRED on refund; null when cancel-only. */
  amount: number | null;
  /** OPTIONAL — defaults to false. */
  cancel?: boolean;
  /** OPTIONAL — defaults to false. */
  refund?: boolean;
  /** OPTIONAL — omit when no restock is intended. */
  restockTo?: RefundRestockTo;
  /** OPTIONAL — defaults to false. */
  notify?: boolean;
  /** REQUIRED — Slack user id of the approver. */
  approvedBy: string;
  /** OPTIONAL — defaults to false. */
  isTest?: boolean;
}

export interface ShopifyUserError {
  field: string[] | null;
  message: string;
  code?: string | null;
}

export interface CancelOutcome {
  jobId: string;
  jobDone: boolean;
}

export interface RefundOutcome {
  refundId: string;
  amount: number;
  currency: string;
  /** ISO timestamp from Shopify. */
  createdAt: string;
}

export interface CreateRefundResponse {
  ok: boolean;
  cancel: CancelOutcome | null;
  refund: RefundOutcome | null;
  errors: ShopifyUserError[];
}
