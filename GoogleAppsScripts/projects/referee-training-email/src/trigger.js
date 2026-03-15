// trigger.js — onFormSubmit entrypoint (active trigger)
//
// Set this function as the trigger:
//   Triggers → Add trigger → onFormSubmit → Form submit event type

import { EMAIL_SOURCE, EMAIL_QUESTION_TITLE } from './config.js';
import { addGuestToSessions } from './calendar.js';
import { sendConfirmationEmail } from './email.js';
import { sendToLambda } from './sendToLambda.js';

/**
 * @param {GoogleAppsScript.Events.FormsOnFormSubmit} e
 */
export function onFormSubmit(e) {
  console.log("=== onFormSubmit triggered ===");

  const response = e.response;
  const allItems = response.getItemResponses();
  const errors = [];

  // Serialize full form response for Lambda debugging
  const rawFormResponse = {
    responseId: response.getId(),
    timestamp: response.getTimestamp().toISOString(),
    respondentEmail: response.getRespondentEmail() || null,
    items: allItems.map((r) => {
      const item = r.getItem();
      const type = item.getType().toString();
      const entry = { title: item.getTitle(), type, response: r.getResponse() };
      if (type === "CHECKBOX_GRID" || type === "GRID") {
        try {
          const g = type === "CHECKBOX_GRID" ? item.asCheckboxGridItem() : item.asGridItem();
          entry.rows = g.getRows();
          entry.columns = g.getColumns();
        } catch (_) {}
      }
      return entry;
    }),
  };

  // 1. Extract name fields
  const firstName = allItems.find((r) =>
    r.getItem().getTitle().toLowerCase() === "first name"
  )?.getResponse()?.trim() || "";

  const lastName = allItems.find((r) =>
    r.getItem().getTitle().toLowerCase() === "last name"
  )?.getResponse()?.trim() || "";

  // 2. Extract email
  let email;
  if (EMAIL_SOURCE === "question") {
    const emailItem = allItems.find((r) =>
      r.getItem().getTitle().toLowerCase() === EMAIL_QUESTION_TITLE.toLowerCase()
    );
    email = emailItem ? emailItem.getResponse().trim() : "";
  } else {
    email = response.getRespondentEmail();
  }

  if (!email) {
    console.error("ABORT: No email found.");
    return;
  }

  // 3. Extract selected sessions
  const sessionItem = allItems.find((r) =>
    r.getItem().getTitle().toLowerCase().includes("select the virtual training session")
  );

  if (!sessionItem) {
    console.error("ABORT: Session question not found.");
    return;
  }

  const rawValue = sessionItem.getResponse();
  const selectedSessions = Array.isArray(rawValue)
    ? rawValue
    : String(rawValue).split(/,\s+(?=Virtual Referee Training)/);
  console.log("Selected sessions:", selectedSessions);

  // 4. Add guest to calendar events
  const confirmed = addGuestToSessions(email, selectedSessions);
  console.log("Confirmed sessions:", confirmed);

  const calendarSuccess = confirmed.length === selectedSessions.length;
  if (!calendarSuccess) {
    const missed = selectedSessions.filter((s) => !confirmed.includes(s));
    errors.push(`Calendar invite failed for: ${missed.join(", ")}`);
  }

  // 5. Send confirmation email
  let emailSuccess = false;
  if (confirmed.length > 0) {
    try {
      const sessionList = confirmed.map((s) => `<li>${s}</li>`).join('');
      const emailFooter = `
        <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; font-size: 14px;">
          <p>Warmly,<br><b>BARS Leadership</b></p>
          <a href="https://www.bigapplerecsports.com" target="_blank">
            <img src="cid:barsLogo" style="width:225px; height:auto; margin-top: 15px;">
          </a>
          <p><strong>Big Apple Rec Sports</strong><br>
          Follow us: <a href="https://www.instagram.com/bigapplerecsports/">Instagram</a> | <a href="https://www.facebook.com/groups/bigapplerecsports">Facebook</a></p>
        </div>
      `;
      sendConfirmationEmail({
        to: email,
        subject: "You're registered for referee training",
        body: `
          Hi ${firstName},<br><br>
          You're confirmed for the following training session(s):<br>
          <ul>${sessionList}</ul>
          Calendar invites have been sent to you.<br><br>
          See you there!
          ${emailFooter}
        `,
      });
      emailSuccess = true;
    } catch (err) {
      errors.push(`Email failed: ${err.message}`);
      console.error("Email error:", err.message);
    }
  } else {
    errors.push("No sessions confirmed — email not sent.");
    console.warn("No sessions confirmed — no email sent for:", email);
  }

  // 6. Notify Lambda
  sendToLambda({
    firstName,
    lastName,
    email,
    success: calendarSuccess && emailSuccess,
    confirmedSessions: confirmed,
    selectedSessions,
    errors,
    rawFormResponse,
  });

  console.log("=== onFormSubmit complete ===");
}
