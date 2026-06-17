/** Per-row outcome captured during waitlist processing. Built up across
 *  Shopify and email steps; consumed by the channel summary bullets. */

import type { League } from "../league/types.ts";

export interface ActionResult {
    rowNumber: number;
    type: "admit" | "remove";
    name: string;
    firstName: string;
    email: string;
    phone?: string;
    league?: League;
    shopifyOk: boolean;
    emailOk: boolean;
    /** True only when a notification email was actually sent (the per-row box was ticked). */
    emailed: boolean;
    shopifyError?: string;
    emailError?: string;
    /** Links resolved during processing, used to build the channel message bullets. */
    customerAdminUrl?: string;
    productUrl?: string;
}
