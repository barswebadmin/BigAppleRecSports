/**
 * Tests for format validators
 * I/O under test:
 * - isDateMMDDYYYY_: accepts 1/5/2025, 01/05/25; rejects 2025/01/05, abc
 * - isTime12h_: accepts 8:00 PM; rejects 20:00
 * - isTimeRange12h_: accepts 8:00 PM - 11:00 PM; rejects 8 PM - 11 PM
 * - isISO8601_: accepts 2025-09-17T23:00:00Z; rejects 2025-09-17 23:00
 * - isDateTimeAllowed_: accepts ISO or MM/DD/YYYY HH:MM AM/PM; rejects others
 */

/// <reference path="../src/helpers/formatValidators.gs" />

function test_formatValidators_dates_() {
  if (!isDateMMDDYYYY_('1/5/2025')) throw new Error('1/5/2025 should pass');
  if (!isDateMMDDYYYY_('01/05/25')) throw new Error('01/05/25 should pass');
  if (isDateMMDDYYYY_('2025/01/05')) throw new Error('2025/01/05 should fail');
  if (isDateMMDDYYYY_('abc')) throw new Error('abc should fail');
}

function test_formatValidators_time_() {
  if (!isTime12h_('8:00 PM')) throw new Error('8:00 PM should pass');
  if (isTime12h_('20:00')) throw new Error('24h 20:00 should fail');
}

function test_formatValidators_range_() {
  if (!isTimeRange12h_('8:00 PM - 11:00 PM')) throw new Error('range should pass');
  if (isTimeRange12h_('8 PM - 11 PM')) throw new Error('range without minutes should fail');
}

function test_formatValidators_iso_() {
  if (!isISO8601_('2025-09-17T23:00:00Z')) throw new Error('ISO should pass');
  if (isISO8601_('2025-09-17 23:00')) throw new Error('non-ISO should fail');
}

function test_formatValidators_allowedDateTime_() {
  if (!isDateTimeAllowed_('2025-09-17T23:00:00Z')) throw new Error('ISO allowed should pass');
  if (!isDateTimeAllowed_('09/17/2025 11:00 PM')) throw new Error('MM/DD/YYYY HH:MM AM/PM should pass');
  if (isDateTimeAllowed_('2025/09/17 23:00')) throw new Error('invalid format should fail');
}


