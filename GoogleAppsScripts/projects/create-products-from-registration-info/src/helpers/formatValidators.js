/**
 * Reusable input format validators for GAS parsing and onEdit warnings
 */

// biome-ignore lint/correctness/noUnusedVariables: exported for tests and onEdit
export function isDateMMDDYYYY(v) {
  const s = String(v || '').trim();
  return /^(0?[1-9]|1[0-2])\/(0?[1-9]|[12][0-9]|3[01])\/(\d{2}|\d{4})$/.test(s);
}

// biome-ignore lint/correctness/noUnusedVariables: exported for tests and onEdit
export function isTime12h(s) {
  const v = String(s || '').trim();
  return /^(0?[1-9]|1[0-2]):[0-5][0-9]\s?(AM|PM)$/i.test(v);
}

// biome-ignore lint/correctness/noUnusedVariables: exported for tests and onEdit
export function isTimeRange12h(s) {
  const v = String(s || '').trim();
  if (!v.includes('-')) return false;
  const parts = v.split('-').map(x => x.trim());
  return parts.length === 2 && isTime12h(parts[0]) && isTime12h(parts[1]);
}

// biome-ignore lint/correctness/noUnusedVariables: exported for tests and onEdit
export function isISO8601(s) {
  const v = String(s || '').trim();
  return /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?Z$/.test(v);
}

// biome-ignore lint/correctness/noUnusedVariables: exported for tests and onEdit
export function isDateTimeAllowed(s) {
  const v = String(s || '').trim();
  if (!v) return false;
  if (isISO8601(v)) return true;
  return /^(0?[1-9]|1[0-2])\/(0?[1-9]|[12][0-9]|3[01])\/(\d{2}|\d{4})\s+(0?[1-9]|1[0-2]):[0-5][0-9]\s?(AM|PM)$/i.test(v);
}



// Format helpers
// biome-ignore lint/correctness/noUnusedVariables: exported for UI formatting
export function formatDateMdYY(v) {
  try {
    if (!v) return '';
    const d = v instanceof Date ? v : new Date(v);
    if (!(d instanceof Date) || isNaN(d.getTime())) return '';
    if (typeof Utilities !== 'undefined' && Utilities.formatDate) {
      return Utilities.formatDate(d, 'America/New_York', 'M/d/yy');
    }
    const m = d.getMonth()+1;
    const day = d.getDate();
    const yy = String(d.getFullYear()).slice(-2);
    return `${m}/${day}/${yy}`;
  } catch (_) {
    return '';
  }
}

// biome-ignore lint/correctness/noUnusedVariables: exported for UI formatting
export function formatDateTimeMdYYhm(v) {
  try {
    if (!v) return '';
    const d = v instanceof Date ? v : new Date(v);
    if (!(d instanceof Date) || isNaN(d.getTime())) return '';
    if (typeof Utilities !== 'undefined' && Utilities.formatDate) {
      return Utilities.formatDate(d, 'America/New_York', 'M/d/yy h:mm a');
    }
    const m = d.getMonth()+1;
    const day = d.getDate();
    const yy = String(d.getFullYear()).slice(-2);
    let h = d.getHours();
    const min = d.getMinutes();
    const ampm = h >= 12 ? 'PM' : 'AM';
    const hr12 = h % 12 === 0 ? 12 : h % 12;
    const mm = String(min).padStart(2, '0');
    return `${m}/${day}/${yy} ${hr12}:${mm} ${ampm}`;
  } catch (_) {
    return '';
  }
}

// Month names: 3-char abbrev with period for Jan-Feb, Apr-Aug, Oct-Nov-Dec; full name for March, June, July, Sept
const MONTH_DISPLAY = ['Jan.', 'Feb.', 'March', 'April', 'May', 'June', 'July', 'Aug.', 'Sept.', 'Oct.', 'Nov.', 'Dec.'];

// biome-ignore lint/correctness/noUnusedVariables: exported for description template
export function formatDateLong(v) {
  try {
    if (!v) return '';
    const d = v instanceof Date ? v : new Date(v);
    if (isNaN(d.getTime())) return '';
    const month = MONTH_DISPLAY[d.getMonth()];
    const day = d.getDate();
    const year = d.getFullYear();
    return `${month} ${day}, ${year}`;
  } catch (_) {
    return '';
  }
}

// biome-ignore lint/correctness/noUnusedVariables: exported for description template
export function formatDateTimeLong(v) {
  try {
    if (!v) return '';
    const d = v instanceof Date ? v : new Date(v);
    if (isNaN(d.getTime())) return '';
    const datePart = formatDateLong(d);
    let h = d.getHours();
    const min = d.getMinutes();
    const ampm = h >= 12 ? 'PM' : 'AM';
    const hr12 = h % 12 === 0 ? 12 : h % 12;
    const mm = String(min).padStart(2, '0');
    return `${datePart} ${hr12}:${mm} ${ampm}`;
  } catch (_) {
    return '';
  }
}
