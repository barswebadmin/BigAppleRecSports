/************************************************************
 * CONFIGURATION
 ************************************************************/

const CALENDAR_ID =
  "c_ec89f4d1e8f2e6f87b6edbcbeeba3c7643c0e8b35d1ef507a58537bbee8d3785@group.calendar.google.com";

const SESSION_EVENTS = {
  "Virtual Referee Training - Session 1 (March 16, 7pm)":
    "NzlvZXBubThzOTc5cmRhMDNhNWkyMjI0ODM@group.calendar.google.com",
  "Virtual Referee Training - Session 2 (March 18, 8pm)":
    "MGdtMW01bm9yczR1M2d0bmVibzJnaWxpaHQ@group.calendar.google.com",
  "Virtual Referee Training - Session 3 (March 19, 8pm)":
    "NmExbjZvMHAwaWkydmxpcWN0dWplOHQxZHY@group.calendar.google.com",
  "Virtual Referee Training - Session 4 (March 21, 11am)":
    "MDlmam52YnIyYXA5b2dxaWNxOWFjOHJhbXQ@group.calendar.google.com"
};

/************************************************************
 * ROW TRACKING (for time-driven processing)
 ************************************************************/

function getLastProcessedRow() {
  const props = PropertiesService.getScriptProperties();
  return Number(props.getProperty("lastProcessedRow")) || 1;
}

function setLastProcessedRow(row) {
  const props = PropertiesService.getScriptProperties();
  props.setProperty("lastProcessedRow", String(row));
}

/************************************************************
 * MAIN TIME-DRIVEN PROCESSOR
 ************************************************************/

function processNewSubmissions() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(
    "Form Responses 1"
  );
  const lastRow = sheet.getLastRow();
  const lastProcessed = getLastProcessedRow();

  console.log("Last processed row:", lastProcessed);
  console.log("Current last row:", lastRow);

  if (lastRow <= lastProcessed) return;

  for (let r = lastProcessed + 1; r <= lastRow; r++) {
    const row = sheet
      .getRange(r, 1, 1, sheet.getLastColumn())
      .getValues()[0];
    handleNewSubmission(sheet, row);
  }

  setLastProcessedRow(lastRow);
}

/************************************************************
 * PROCESS A SINGLE FORM SUBMISSION
 ************************************************************/

function handleNewSubmission(sheet, row) {
  const headers = sheet
    .getRange(1, 1, 1, sheet.getLastColumn())
    .getValues()[0];
  console.log("Headers:", headers);

  // Use ONLY the "Email" column
  const emailCol = headers.findIndex(
    (h) => h.trim().toLowerCase() === "email"
  );

  // Match the long training session question
  const sessionCol = headers.findIndex((h) =>
    h.toLowerCase().includes("select the virtual training session")
  );

  console.log("Email column index:", emailCol);
  console.log("Session column index:", sessionCol);

  if (emailCol === -1 || sessionCol === -1) {
    console.log("ERROR: Could not find required columns");
    return;
  }

  const email = row[emailCol];
  const sessionField = row[sessionCol];

  console.log("Email:", email);
  console.log("Session field:", sessionField);

  if (!email || !sessionField) return;

  /************************************************************
   * CORRECT SESSION SPLITTING
   * Split ONLY between sessions, not inside parentheses
   ************************************************************/

  const selectedSessions = sessionField.split(
    /,\s+(?=Virtual Referee Training)/
  );
  console.log("Parsed sessions:", selectedSessions);

  const calendar = CalendarApp.getCalendarById(CALENDAR_ID);
  const confirmedSessions = [];

  /************************************************************
   * FUZZY MATCH SESSION NAMES → EVENT IDS
   ************************************************************/

  selectedSessions.forEach((sessionName) => {
    console.log("Processing session:", sessionName);

    const matchedKey = Object.keys(SESSION_EVENTS).find((key) =>
      sessionName.includes(key)
    );

    if (!matchedKey) {
      console.log("No matching session key for:", sessionName);
      return;
    }

    const eventId = SESSION_EVENTS[matchedKey];
    console.log("Matched event ID:", eventId);

    const event = calendar.getEventById(eventId);
    if (!event) {
      console.log("Event not found:", eventId);
      return;
    }

    event.addGuest(email);
    confirmedSessions.push(matchedKey);
  });

  console.log("Confirmed sessions:", confirmedSessions);

  /************************************************************
   * SEND CONFIRMATION EMAIL
   ************************************************************/

  if (confirmedSessions.length > 0) {
    const listHtml = confirmedSessions
      .map((s) => `<li>${s}</li>`)
      .join("");

    MailApp.sendEmail({
      to: email,
      subject: "You're registered for referee training",
      htmlBody: `
        Hi there,<br><br>
        You're confirmed for the following training sessions:<br>
        <ul>${listHtml}</ul>
        Calendar invites have been sent to you.<br><br>
        See you there!<br>
        – Richard
      `
    });

    console.log("Confirmation email sent to:", email);
  }
}
function listEvents() {
  const cal = CalendarApp.getCalendarById(CALENDAR_ID);
  const events = cal.getEvents(
    new Date("2026-03-01"),
    new Date("2026-03-31")
  );

  events.forEach(e => {
    console.log("TITLE:", e.getTitle());
    console.log("ID:", e.getId());
  });
}