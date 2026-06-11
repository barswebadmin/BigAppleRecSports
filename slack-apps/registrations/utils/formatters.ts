import type { League } from "../types/league.ts";

const STORE_BASE = "https://www.bigapplerecsports.com";

export function buildLoginUrl(productHandle: string): string {
    return `${STORE_BASE}/customer_authentication/login?return_to=%2Fproducts%2F${productHandle}`;
}

export function formatDivision(division: string): string {
    return division.toLowerCase() === "wtnb" ? "WTNB+ Division" : "Open Division";
}

export function formatDivisionShort(division: string): string {
    return division.toLowerCase() === "wtnb" ? "WTNB" : "Open";
}

export function formatProductHandle(league: League): string {
    return `${league.year}-${league.season}-${league.sport}-${league.day}-${league.division}div`;
}

export function formatWaitlistTag(league: League): string {
    return `${formatProductHandle(league)}-waitlist`;
}

export function formatVeteranTag(league: League): string {
    return `${formatProductHandle(league)}-veteran`;
}

export function capitalize(s: string): string {
    return s.charAt(0).toUpperCase() + s.slice(1);
}

export function formatSportLeadershipEmailAddress(league: League): string {
    return `${league.sport}.${league.day}.${league.division}@bigapplerecsports.com`;
}

export function formatSportLeadershipEmailSenderName(league: League): string {
    return `Big Apple ${capitalize(league.sport)}`;
}

export function formatLeagueLabel(league: League): string {
    return `${capitalize(league.sport)} - ${capitalize(league.day)} - ${
        formatDivision(league.division)
    }`;
}

export function leagueToOptionValue(lg: League): string {
    return [lg.year, lg.season, lg.sport, lg.day, lg.division].join("|");
}

export function formatLeagueLabelShort(league: League): string {
    return `${capitalize(league.day)} ${formatDivisionShort(league.division)} ${
        capitalize(league.sport)
    }`;
}

function digitsOnly(phone: string): string {
    return phone.replace(/\D/g, "");
}

/** Normalize a phone number to E.164 format (+1XXXXXXXXXX). Returns null if invalid. */
export function normalizePhone(raw: string): string | null {
    const digits = digitsOnly(raw);
    if (digits.length === 10) return `+1${digits}`;
    if (digits.length === 11 && digits.startsWith("1")) return `+${digits}`;
    return null;
}

/** Check if a raw phone string is valid (10 digits, or 11 with leading 1). */
export function isValidPhone(raw: string): boolean {
    return normalizePhone(raw) !== null;
}

/** Compare two phone numbers after normalization. */
export function phonesMatch(a: string | null, b: string | null): boolean {
    if (!a || !b) return false;
    const normA = normalizePhone(a);
    const normB = normalizePhone(b);
    if (!normA || !normB) return false;
    return normA === normB;
}
