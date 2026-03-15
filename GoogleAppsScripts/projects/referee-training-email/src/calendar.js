// calendar.js — calendar guest management

import { CALENDAR_ID, SESSION_EVENTS } from './config.js';

/**
 * Given a list of session name strings selected by the user, add the email
 * as a guest to each matching calendar event.
 *
 * @param {string} email
 * @param {string[]} selectedSessions - raw option strings from the form response
 * @returns {string[]} confirmed session names that were successfully matched + updated
 */
export function addGuestToSessions(email, selectedSessions) {
  console.log("Looking up calendar:", CALENDAR_ID);
  const calendar = CalendarApp.getCalendarById(CALENDAR_ID);

  if (!calendar) {
    console.error("ABORT: Calendar not found — check CALENDAR_ID in config.js");
    return [];
  }
  console.log("Calendar found:", calendar.getName());

  const confirmed = [];

  selectedSessions.forEach((sessionName) => {
    console.log("  Matching session:", sessionName);

    const matchedKey = Object.keys(SESSION_EVENTS).find((key) =>
      sessionName.includes(key)
    );

    if (!matchedKey) {
      console.warn("  No config key matched for:", sessionName);
      return;
    }
    console.log("  Matched config key:", matchedKey);

    const eventId = SESSION_EVENTS[matchedKey];
    console.log("  Looking up event ID:", eventId);
    const event = calendar.getEventById(eventId);

    if (!event) {
      console.error("  Event not found — ID may be stale. Run listEvents() to verify. ID:", eventId);
      return;
    }
    console.log("  Event found:", event.getTitle());

    event.addGuest(email);
    confirmed.push(matchedKey);
    console.log("  Guest added:", email);
  });

  return confirmed;
}

/** Debug helper — run manually to verify event IDs are still valid. */
export function listEvents() {
  const cal = CalendarApp.getCalendarById(CALENDAR_ID);
  cal
    .getEvents(new Date("2026-03-01"), new Date("2026-03-31"))
    .forEach((e) => {
      console.log("TITLE:", e.getTitle(), "| ID:", e.getId());
    });
}
