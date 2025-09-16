/**
 * Reusable input format validators for GAS parsing and onEdit warnings
 */

// biome-ignore lint/correctness/noUnusedVariables: exported for tests and onEdit
function isDateMMDDYYYY_(v) {
  const s = String(v || '').trim();
  return /^(0?[1-9]|1[0-2])\/(0?[1-9]|[12][0-9]|3[01])\/(\d{2}|\d{4})$/.test(s);
}

// biome-ignore lint/correctness/noUnusedVariables: exported for tests and onEdit
function isTime12h_(s) {
  const v = String(s || '').trim();
  return /^(0?[1-9]|1[0-2]):[0-5][0-9]\s?(AM|PM)$/i.test(v);
}

// biome-ignore lint/correctness/noUnusedVariables: exported for tests and onEdit
function isTimeRange12h_(s) {
  const v = String(s || '').trim();
  if (!v.includes('-')) return false;
  const parts = v.split('-').map(x => x.trim());
  return parts.length === 2 && isTime12h_(parts[0]) && isTime12h_(parts[1]);
}

// biome-ignore lint/correctness/noUnusedVariables: exported for tests and onEdit
function isISO8601_(s) {
  const v = String(s || '').trim();
  return /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?Z$/.test(v);
}

// biome-ignore lint/correctness/noUnusedVariables: exported for tests and onEdit
function isDateTimeAllowed_(s) {
  const v = String(s || '').trim();
  if (!v) return false;
  if (isISO8601_(v)) return true;
  return /^(0?[1-9]|1[0-2])\/(0?[1-9]|[12][0-9]|3[01])\/(\d{2}|\d{4})\s+(0?[1-9]|1[0-2]):[0-5][0-9]\s?(AM|PM)$/i.test(v);
}


