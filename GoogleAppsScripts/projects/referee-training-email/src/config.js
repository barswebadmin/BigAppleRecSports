// config.js — all hardcoded IDs and session mappings

// EMAIL_SOURCE controls how the respondent's email is collected.
//   "verified"  — uses Google's built-in "Collect email addresses" (verified, signed-in Google account)
//   "question"  — reads from a form question titled EMAIL_QUESTION_TITLE (unverified, works without sign-in)
export const EMAIL_SOURCE = "question"; // TODO: set to "verified" to use Google sign-in email instead

// Only used when EMAIL_SOURCE = "question"
export const EMAIL_QUESTION_TITLE = "Email";

export const CALENDAR_ID =
  "c_ec89f4d1e8f2e6f87b6edbcbeeba3c7643c0e8b35d1ef507a58537bbee8d3785@group.calendar.google.com";

// Keys must match (or be contained in) the form's checkbox option text exactly.
export const SESSION_EVENTS = {
  "Virtual Referee Training - Session 1 (March 16, 7pm)":
    "79oepnm8s979rda03a5i222483@google.com",
  "Virtual Referee Training - Session 2 (March 18, 8pm)":
    "0gm1m5nors4u3gtnebo2giliht@google.com",
  "Virtual Referee Training - Session 3 (March 19, 8pm)":
    "6a1n6o0p0ii2vliqctuje8t1dv@google.com",
  "Virtual Referee Training - Session 4 (March 21, 11am)":
    "09fjnvbr2ap9ogqicq9ac8ramt@google.com",
};
