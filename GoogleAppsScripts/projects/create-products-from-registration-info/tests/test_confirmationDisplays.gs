/**
 * Tests for confirmation displays not throwing with missing fields,
 * and rendering [Not Found] placeholders.
 */
/// <reference path="../src/core/portedFromProductCreateSheet/createShopifyProduct.gs" />

function test_buildConfirmationDisplay_handles_missing_fields_() {
  const incomplete = {
    sportName: 'Kickball',
    // missing many fields deliberately
    seasonStartDate: null,
    seasonEndDate: undefined,
    price: '',
    totalInventory: null,
    earlyRegistrationStartDateTime: '',
    openRegistrationStartDateTime: null
  };

  var text = buildConfirmationDisplay_(incomplete);
  if (typeof text !== 'string' || text.length === 0) throw new Error('Expected non-empty confirmation text');
  if (!text.includes('[Not Found]')) throw new Error('Expected placeholder [Not Found] to appear for missing fields');
}

function test_buildErrorDisplay_handles_missing_fields_() {
  const incomplete = {
    sportName: 'Dodgeball',
    seasonStartDate: null,
    seasonEndDate: null,
    price: null,
    totalInventory: null
  };
  var text = buildErrorDisplay_(incomplete, ['Season Start Date', 'Season End Date', 'Price', 'Total Inventory']);
  if (typeof text !== 'string' || text.length === 0) throw new Error('Expected non-empty error display text');
  if (!text.includes('[Not Found]')) throw new Error('Expected [Not Found] placeholders in error display');
}


