/**
 * Time parsing functions for parse-registration-info
 * Parse time ranges and create Date objects with time-only data
 *
 * @fileoverview Time range parsing with AM/PM logic
 */

/**
 * Parse time range with primary and alternative sessions
 */
function parseTimeRangeBothSessions_(s) {
  const out = {
    primaryStartDateOnly: '',
    primaryEndDateOnly: '',
    altStartDateOnly: '',
    altEndDateOnly: '',
  };
  if (!s || !s.trim()) return out;

  const partRegex = /(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\s*-\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)?/i;
  const segments = s.split(/[&+]|and/gi).map(t => t.trim()).filter(Boolean);

  if (segments[0]) {
    const m1 = segments[0].replace(/[–—]/g, '-').match(partRegex);
    if (m1) {
      const p = tm_(m1);
      out.primaryStartDateOnly = p.start;
      out.primaryEndDateOnly = p.end;
    }
  }
  if (segments[1]) {
    const m2 = segments[1].replace(/[–—]/g, '-').match(partRegex);
    if (m2) {
      const p2 = tm_(m2);
      out.altStartDateOnly = p2.start;
      out.altEndDateOnly = p2.end;
    }
  }
  return out;

  function tm_(m) {
    // m: [full, sh, sm, sap, eh, em, eap]
    let [, sh, sm, sap, eh, em, eap] = m;
    const shNum = parseInt(sh, 10);
    const ehNum = parseInt(eh, 10);

    sm = sm || '00';
    em = em || '00';

    // Normalize provided meridiems to lowercase
    sap = sap ? sap.toLowerCase() : '';
    eap = eap ? eap.toLowerCase() : '';

    // If only one side has AM/PM, copy it to the other (original behavior)
    if (!sap && eap) sap = eap;
    if (sap && !eap) eap = sap;

    // --- NEW DEFAULTS ---
    // Default start: PM unless 10 or 11 → AM
    if (!sap) {
      sap = (shNum === 10 || shNum === 11) ? 'am' : 'pm';
    }

    // Infer end if missing
    if (!eap) {
      if (sap === 'pm') {
        // Evening leagues: almost always PM
        eap = 'pm';
      } else {
        // Start is AM (only when start is 10 or 11 per rule)
        if (ehNum === 12) {
          // 10-12 or 11-12 → crosses noon → PM
          eap = 'pm';
        } else if (ehNum > shNum && ehNum <= 11) {
          // e.g., 10-11 → still AM
          eap = 'am';
        } else {
          // e.g., 11-1 → PM; 11-2 → PM; 10-1 → PM
          eap = 'pm';
        }
      }
    }

    const start = timeOnlyDate_(to24h(shNum, parseInt(sm,10), sap).h, parseInt(sm,10), 'pm'); // 'pm' ignored inside helper
    const end   = timeOnlyDate_(to24h(ehNum, parseInt(em,10), eap).h, parseInt(em,10), 'pm');

    return { start, end };
  }
}

/**
 * Convert 12-hour to 24-hour format
 */
function to24h(h12, min, meridiem) {
  let h24 = h12;
  if (meridiem === 'am' && h12 === 12) h24 = 0;
  if (meridiem === 'pm' && h12 !== 12) h24 += 12;
  return { h: h24, m: min };
}

/**
 * Create a Date object with only time information (date part is fixed)
 */
function timeOnlyDate_(hour24, minute, ignoredMeridiem) {
  const d = new Date(2000, 0, 1, hour24, minute, 0, 0);
  return d;
}
