/** Pure status predicates over waitlist entries. */

import { ContactedStatuses, type WaitlistEntry } from "./types.ts";

/** True when the entry's status indicates the person has already been
 *  contacted (case-insensitive substring match against `ContactedStatuses`). */
export function isContacted(entry: WaitlistEntry): boolean {
    if (!entry.status) return false;
    const norm = entry.status.toLowerCase();
    return ContactedStatuses.some((k) => norm.includes(k));
}
