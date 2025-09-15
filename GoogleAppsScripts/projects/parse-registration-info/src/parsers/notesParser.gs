/**
 * Notes parsing functions for parse-registration-info
 * Extract special dates and information from notes column
 *
 * @fileoverview Parse notes column for special dates and events
 * @requires dateParser.gs
 */

// Import references for editor support
/// <reference path="dateParser.gs" />

/**
 * Parse notes column (C) for special dates and events
 */
function parseNotes_(cVal, sportStartTime, unresolved) {
  const res = {
    orientationDate: '',
    scoutNightDate: '',
    openingPartyDate: '',
    rainDate: '',
    closingPartyDate: '',
    offDatesFromNotes: [],
    altTimesFromNotes: null,
    typesFromNotes: []
  };

  const text = (cVal || '').replace(/\r/g, '').trim();
  if (!text) return res;

  // Helper: parse a date string; if no time found, apply sportStartTime's time
  function parseWithSportTime_(s) {
    const dt = parseFlexible_(s, { assumeDateTime: true });
    if (!dt) return '';
    if (sportStartTime instanceof Date && !isNaN(sportStartTime)) {
      if (!/\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b/i.test(s) && !/\b\d{1,2}:\d{2}\b/.test(s)) {
        dt.setHours(sportStartTime.getHours(), sportStartTime.getMinutes(), 0, 0);
      }
    }
    return dt;
  }

  // ---- Orientation-like lines ----
  const orientMatch = text.match(/(?:newbie\s+night|open\s*play)(?:\/\s*open\s*play)?\s*(?:-|:)?\s*([a-z]{3,9}\.?[\s.,]*\d{1,2}(?:st|nd|rd|th)?(?:,?\s*\d{2,4})?|\d{1,2}[\/\-]\d{1,2}(?:[\/\-]\d{2,4})?)/i);
  if (orientMatch) {
    const dt = parseWithSportTime_(orientMatch[1]);
    if (dt) {
      res.orientationDate = dt;
      // Successfully found orientation date - remove from unresolved
      const index = unresolved.indexOf("newPlayerOrientationDateTime");
      if (index > -1) unresolved.splice(index, 1);
    }
  }

  // ---- Opening Party ----
  const openingPartyMatch = text.match(/opening\s+party\s*:\s*((?:date\s+)?tbd|[a-z]{3,9}\.?[\s.,]*\d{1,2}(?:st|nd|rd|th)?(?:,?\s*\d{2,4})?|\d{1,2}[\/\-]\d{1,2}(?:[\/\-]\d{2,4})?)/i);
  if (openingPartyMatch) {
    if (/(?:date\s+)?tbd/i.test(openingPartyMatch[1])) {
      res.openingPartyDate = 'TBD';
      // Successfully found opening party date (TBD) - remove from unresolved
      const index = unresolved.indexOf("openingPartyDate");
      if (index > -1) unresolved.splice(index, 1);
    } else {
      const d = parseDateFlexibleDateOnly_(openingPartyMatch[1], unresolved, "openingPartyDate");
      if (d) res.openingPartyDate = d;
    }
  }

  // ---- Scout Night ----
  const scoutMatch = text.match(/scout\s+night\s*:\s*([a-z]{3,9}\.?[\s.,]*\d{1,2}(?:st|nd|rd|th)?(?:,?\s*\d{2,4})?|\d{1,2}[\/\-]\d{1,2}(?:[\/\-]\d{2,4})?)/i);
  if (scoutMatch) {
    const dt = parseWithSportTime_(scoutMatch[1]);
    if (dt) {
      res.scoutNightDate = dt;
      // Successfully found scout night date - remove from unresolved
      const index = unresolved.indexOf("scoutNightDateTime");
      if (index > -1) unresolved.splice(index, 1);
    }
  }

  // ---- Rain Date ----
  const rainMatch = text.match(/rain\s+date\s*:\s*([a-z]{3,9}\.?[\s.,]*\d{1,2}(?:st|nd|rd|th)?(?:,?\s*\d{2,4})?|\d{1,2}[\/\-]\d{1,2}(?:[\/\-]\d{2,4})?)/i);
  if (rainMatch) {
    const d = parseDateFlexibleDateOnly_(rainMatch[1], unresolved, "rainDate");
    if (d) res.rainDate = d;
  }

  // ---- Closing Party ----
  const closingMatch = text.match(/closing\s+party\s*:\s*((?:date\s+)?tbd|[a-z]{3,9}\.?[\s.,]*\d{1,2}(?:st|nd|rd|th)?(?:,?\s*\d{2,4})?|\d{1,2}[\/\-]\d{1,2}(?:[\/\-]\d{2,4})?)/i);
  if (closingMatch) {
    if (/(?:date\s+)?tbd/i.test(closingMatch[1])) {
      res.closingPartyDate = 'TBD';
      // Successfully found closing party date (TBD) - remove from unresolved
      const index = unresolved.indexOf("closingPartyDate");
      if (index > -1) unresolved.splice(index, 1);
    } else {
      const d = parseDateFlexibleDateOnly_(closingMatch[1], unresolved, "closingPartyDate");
      if (d) res.closingPartyDate = d;
    }
  }

  // ---- Off Dates ----
  // Handle various patterns: "off dates:", "no games:", "skipping", etc.
  const offDatesPattern = /(?:off|no\s+games?|cancelled?|skipping)\s*(?:dates?)?\s*(?::|on)?\s*([0-9\/,\s\-and]+)/gi;
  let offMatch;
  while ((offMatch = offDatesPattern.exec(text)) !== null) {
    const dateStr = offMatch[1];
    // Split by common separators: comma, 'and', spaces, dashes
    const dates = dateStr.split(/[,\s]+|and/).filter(Boolean);

    for (const date of dates) {
      // Match MM/DD or MM/DD/YY format
      if (/^\d{1,2}\/\d{1,2}(?:\/\d{2,4})?$/.test(date.trim())) {
        res.offDatesFromNotes.push(date.trim());
      }
    }
  }

  // ---- Alternative Times ----
  const altTimeMatch = text.match(/(?:alt|alternative)\s+time\s*:\s*(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)\s*-\s*(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)/i);
  if (altTimeMatch) {
    const startTime = parseFlexible_(altTimeMatch[1], { assumeDateTime: true });
    const endTime = parseFlexible_(altTimeMatch[2], { assumeDateTime: true });
    if (startTime && endTime) {
      res.altTimesFromNotes = {
        start: startTime,
        end: endTime
      };
    }
  }

  // ---- Types from Notes ----
  if (/\bdraft\b/i.test(text)) res.typesFromNotes.push('Draft');
  if (/\brandomized\b/i.test(text)) res.typesFromNotes.push('Randomized Teams');
  if (/\bbuddy\s*signup\b/i.test(text)) res.typesFromNotes.push('Buddy Sign-up');
  if (/\bcaptain\s*signup\b/i.test(text)) res.typesFromNotes.push('Captain Signup');

  return res;
}
