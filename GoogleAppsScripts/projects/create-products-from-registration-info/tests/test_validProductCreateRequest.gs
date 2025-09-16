/**
 * Tests for validProductCreateRequest_ helper
 * Verifies: flat→nested canonicalization and required-field validation behavior
 */

// Import references for editor support
/// <reference path="../src/helpers/normalizers.gs" />

function test_validProductCreateRequest_roundtrip_() {
  console.log('🧪 validProductCreateRequest_: roundtrip canonicalization');

  const flat = {
    sportName: 'Dodgeball',
    // top-level fields that should be nested
    season: 'Fall',
    year: 2025,
    dayOfPlay: 'Tuesday',
    division: 'Open',
    location: 'Elliott Center (26th St & 9th Ave)',
    leagueStartTime: '8:00 PM',
    leagueEndTime: '11:00 PM',
    alternativeStartTime: '9:00 PM',
    alternativeEndTime: '12:00 AM',
    // important dates
    seasonStartDate: '10/15/2025',
    seasonEndDate: '12/10/2025',
    openRegistrationStartDateTime: '2025-09-17T23:00:00Z',
    // optional info
    socialOrAdvanced: 'Social',
    sportSubCategory: 'Foam',
    types: ['Buddy Sign-up'],
    // inventory
    price: 150,
    totalInventory: 64,
    numberVetSpotsToReleaseAtGoLive: 40
  };

  const nested = validProductCreateRequest_(flat);

  // Assert canonical nested locations
  if (nested.regularSeasonBasicDetails.season !== 'Fall') throw new Error('season not nested');
  if (nested.regularSeasonBasicDetails.leagueStartTime !== '8:00 PM') throw new Error('leagueStartTime not nested');
  if (nested.importantDates.seasonStartDate !== '10/15/2025') throw new Error('seasonStartDate not nested');
  if (nested.optionalLeagueInfo.socialOrAdvanced !== 'Social') throw new Error('socialOrAdvanced not nested');
  if (nested.inventoryInfo.totalInventory !== 64) throw new Error('totalInventory not nested');

  console.log('✅ validProductCreateRequest_: roundtrip canonicalization passed');
}

function test_validProductCreateRequest_missing_required_() {
  console.log('🧪 validProductCreateRequest_: missing required fields');

  const bad = {
    sportName: 'Kickball',
    // intentionally omit seasonStartDate/End and inventory
    year: 2025,
    season: 'Spring',
    dayOfPlay: 'Saturday',
    division: 'Open',
    location: 'Dewitt Clinton Park',
    leagueStartTime: '10:00 AM',
    leagueEndTime: '12:00 PM'
  };

  let threw = false;
  try {
    validProductCreateRequest_(bad);
  } catch (e) {
    threw = true;
    const msg = String(e);
    if (!msg.includes('importantDates.seasonStartDate')) throw new Error('missing seasonStartDate should be reported');
    if (!msg.includes('inventoryInfo.totalInventory')) throw new Error('missing totalInventory should be reported');
  }
  if (!threw) throw new Error('expected error not thrown for missing requireds');

  console.log('✅ validProductCreateRequest_: missing required fields test passed');
}


