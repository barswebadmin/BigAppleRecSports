import { ShopifyClient } from "@shared/utils/ShopifyClient";
import { loadEnv } from "@shared/utils/loadEnv";

loadEnv();

const shopify = new ShopifyClient();

// Format helpers
const formatDateOnly = (date: Date | string): string => {
  if (!date) return "";
  const d = new Date(date);
  return d.toLocaleDateString("en-US", { year: "2-digit", month: "numeric", day: "numeric" });
};

const formatTimeOnly = (date: Date | string): string => {
  if (!date) return "";
  const d = new Date(date);
  return d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", hour12: true });
};

export interface PriceSchedulePayload {
  sport: string;
  day: string;
  division: string;
  productGid: string;
  openVariantGid: string;
  waitlistVariantGid: string;
  price: number;
  seasonStartDate: string; // formatted
  sportStartTime: string;  // formatted
  offDatesCommaSeparated: string;
}

export const schedulePriceChange = async (payload: PriceSchedulePayload): Promise<string> => {
	console.log(JSON.stringify(payload,null,2))
  const endpoint = process.env.PRICE_SCHEDULER_ENDPOINT;
  if (!endpoint) throw new Error("Missing PRICE_SCHEDULER_ENDPOINT in env");

  const response = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  console.log('sending')

  const text = await response.text();
  if (!response.ok) throw new Error(`Error scheduling price change: ${text}`);
  return text;
};
