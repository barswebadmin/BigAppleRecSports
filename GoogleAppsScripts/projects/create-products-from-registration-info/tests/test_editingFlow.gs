/**
 * Test invariant: updating one field must not change any other field.
 * We unit-test the pure function updateFieldValue_ for this guarantee.
 */
/// <reference path="../src/core/portedFromProductCreateSheet/createShopifyProduct.gs" />

function test_update_one_field_does_not_mutate_others_() {
  const before = {
    sportName: 'Kickball',
    leagueStartTime: '8:00 PM',
    leagueEndTime: '10:00 PM',
    price: 150,
    totalInventory: 192
  };

  // Update field number for leagueStartTime per getEditableFieldsMeta_ ordering.
  const meta = getEditableFieldsMeta_();
  const idx = meta.findIndex(m => m.key === 'leagueStartTime');
  if (idx < 0) throw new Error('leagueStartTime not found in editable meta');

  const after = updateFieldValue_(before, idx + 1, '9:00 PM');

  // Ensure only leagueStartTime changed
  if (after.leagueStartTime !== '9:00 PM') throw new Error('leagueStartTime should be updated');
  if (after.leagueEndTime !== before.leagueEndTime) throw new Error('leagueEndTime should not auto-change');
  if (after.price !== before.price) throw new Error('price should not change');
  if (after.totalInventory !== before.totalInventory) throw new Error('totalInventory should not change');
  if (after.sportName !== before.sportName) throw new Error('sportName should not change');
}


