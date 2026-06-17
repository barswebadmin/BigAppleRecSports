/** Domain-agnostic string helpers. */

export function capitalize(s: string): string {
    return s.charAt(0).toUpperCase() + s.slice(1);
}

export function titlecase(s: string): string {
    return s.charAt(0).toUpperCase() + s.slice(1).toLowerCase();
}

export function formatMoney(n: number | null | undefined): string {
    return n === null || n === undefined ? "—" : `$${n.toFixed(2)}`;
}
