import { ShopifyClient } from "@shared/utils/ShopifyClient";
import { loadEnv } from "@shared/utils/loadEnv";
import {
  formatDateOnly,
  formatTimeOnly,
  formatOffDates
} from "@shared/utils/dateUtils/dateUtils";

loadEnv();

const shopify = new ShopifyClient();

export interface DateInput {
  type: string;
  data: string
}
export interface PriceSchedulePayload {
  sport: string;
  day: string;
  division: string;
  productGid: string;
  openVariantGid: string;
  waitlistVariantGid: string;
  price: number | string;
  seasonStartDate: DateInput | string;
  sportStartTime: DateInput | string;
  offDatesRaw?: DateInput;
  offDatesCommaSeparated?: string;
}

function isValidDateString(input: string): boolean {
  return /^\d{1,2}\/\d{1,2}\/\d{2}$/.test(input.trim());
}

function isValidTimeString(input: string): boolean {
  return /^\d{1,2}:\d{2} (AM|PM)$/i.test(input.trim());
}

function normalizeDateField(field: DateInput | string): string {
  if (typeof field === "string") return field;

  if (field.type === "string") {
    if (!isValidDateString(field.data)) {
      throw new Error(`Invalid date format (expected M/d/yy): ${field.data}`);
    }
    return field.data;
  }

  if (field.type === "object") {
    return formatDateOnly(new Date(field.data));
  }

  throw new Error("Unrecognized date field input");
}

function normalizeTimeField(field: DateInput | string): string {
  if (typeof field === "string") return field;

  if (field.type === "string") {
    if (!isValidTimeString(field.data)) {
      throw new Error(`Invalid time format (expected h:mm AM/PM): ${field.data}`);
    }
    return field.data;
  }

  if (field.type === "object") {
    return formatTimeOnly(new Date(field.data));
  }

  throw new Error("Unrecognized time field input");
}

export const schedulePriceChange = async (payload: PriceSchedulePayload): Promise<string> => {
  const endpoint = process.env.PRICE_SCHEDULER_ENDPOINT;
  if (!endpoint) throw new Error("Missing PRICE_SCHEDULER_ENDPOINT in env");

  try {
    // const response = await fetch(endpoint, {
    //   method: "POST",
    //   headers: { "Content-Type": "application/json" },
    //   body: JSON.stringify(payload)
    // });

    // const text = await response.text();
    // if (!response.ok) throw new Error(`Error scheduling price change: ${text}`);
    // return text;

    const formattedPayload: PriceSchedulePayload = {
      ...payload, 
      productGid: `gid://shopify/Product/${payload.productGid.split('/').pop()}`,
      price: typeof payload.price === 'number' ? payload.price : Number(payload.price),
      seasonStartDate: normalizeDateField(payload.seasonStartDate),
      sportStartTime: normalizeTimeField(payload.sportStartTime),
      offDatesCommaSeparated: payload.offDatesRaw ? formatOffDates(payload.offDatesRaw) : "",
    }

    console.log(`raw payload: \n ${JSON.stringify(payload,null,2)} \n \n`)
    console.log(`formatted payload: \n ${JSON.stringify(formattedPayload,null,2)}`)
    return 'ok!'
  } catch(e: unknown) {
    return JSON.stringify(e)
  }
  
};