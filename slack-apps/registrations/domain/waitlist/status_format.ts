/** Status-column write formatting. `formatStatusTimestamp` is injectable so a
 *  multi-row run pins the same clock across every row's status text. */

/** Format `now` as `M/D at h:mm am/pm` in local time. `now` is injectable so the
 *  caller controls the clock — a multi-row run pins the same timestamp across
 *  all rows, and tests can pass a fixed Date. Defaults to `new Date()` only as a
 *  convenience for the single-call site that doesn't care about pinning. */
export function formatStatusTimestamp(now: Date = new Date()): string {
    const month = now.getMonth() + 1;
    const day = now.getDate();
    let hours = now.getHours();
    const minutes = now.getMinutes().toString().padStart(2, "0");
    const ampm = hours >= 12 ? "pm" : "am";
    hours = hours % 12 || 12;
    return `${month}/${day} at ${hours}:${minutes} ${ampm}`;
}

/** Build the Status-column cell text for a waitlist action and timestamp. */
export function statusText(type: string, timestamp: string): string {
    switch (type) {
        case "admit":
            return `Admitted on ${timestamp}`;
        case "remove":
            return `Cancelled on ${timestamp}`;
        case "order":
            return `Registered on ${timestamp}`;
        default:
            return `Updated on ${timestamp}`;
    }
}
