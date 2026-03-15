/**
 * Main product creation orchestrator
 * Coordinates the entire product creation workflow from parsing to creation
 *
 * @fileoverview Main orchestrator for product creation workflow
 * @requires ../data/productDataProcessing.gs
 * @requires ../ui/productCreationDialogs.gs
 * @requires ../sheet/cellMapping.gs
 * @requires ../core/portedFromProductCreateSheet/shopifyProductCreation.gs
 * @requires ../helpers/normalizers.gs
 */

import { parseRowDataForProductCreation } from '../data/productDataProcessing.js';
import { calculateUnresolvedFieldsForParsedData } from '../validators/fieldValidation.js';
import { createProductFromRowData } from './portedFromProductCreateSheet/shopifyProductCreation.js';
import { writeProductCreationResults } from '../sheet/cellMapping.js';

/**
 * Flatten product data for Shopify API
 * Converts nested structure to flat structure expected by createProductFromRowData
 */
export function flattenForShopifyAPI(data) {
  const flat = {};
  
  // Top-level fields
  flat.sportName = data.sportName;
  flat.year = data.year;
  flat.season = data.season;
  flat.dayOfPlay = data.dayOfPlay;
  flat.division = data.division;
  flat.location = data.location;
  flat.price = data.inventoryInfo?.price ?? data.price;
  flat.totalInventory = data.inventoryInfo?.totalInventory ?? data.totalInventory;
  flat.totalWeeks = data.inventoryInfo?.totalWeeks ?? data.totalWeeks;
  flat.leagueContactEmail = data.leagueContactEmail;
  flat.vetStatusDeterminedBy = data.vetStatusDeterminedBy;
  flat.gameDuration = data.gameDuration;
  
  // From regularSeasonBasicDetails
  if (data.regularSeasonBasicDetails) {
    flat.leagueStartTime = data.regularSeasonBasicDetails.leagueStartTime || data.leagueStartTime;
    flat.leagueEndTime = data.regularSeasonBasicDetails.leagueEndTime || data.leagueEndTime;
    flat.alternativeStartTime = data.regularSeasonBasicDetails.alternativeStartTime || data.alternativeStartTime;
    flat.alternativeEndTime = data.regularSeasonBasicDetails.alternativeEndTime || data.alternativeEndTime;
  } else {
    flat.leagueStartTime = data.leagueStartTime;
    flat.leagueEndTime = data.leagueEndTime;
    flat.alternativeStartTime = data.alternativeStartTime;
    flat.alternativeEndTime = data.alternativeEndTime;
  }
  
  // From optionalLeagueInfo
  if (data.optionalLeagueInfo) {
    flat.levelOfPlay = data.optionalLeagueInfo.levelOfPlay || data.levelOfPlay;
    flat.teamAssignment = data.optionalLeagueInfo.teamAssignment || data.teamAssignment;
    flat.dodgeballBallType = data.optionalLeagueInfo.dodgeballBallType || data.dodgeballBallType;
  } else {
    flat.levelOfPlay = data.levelOfPlay;
    flat.teamAssignment = data.teamAssignment;
    flat.dodgeballBallType = data.dodgeballBallType;
  }
  
  // From importantDates
  if (data.importantDates) {
    flat.seasonStartDate = data.importantDates.seasonStartDate || data.seasonStartDate;
    flat.seasonEndDate = data.importantDates.seasonEndDate || data.seasonEndDate;
    flat.vetRegistrationStartDateTime = data.importantDates.vetRegistrationStartDateTime || data.vetRegistrationStartDateTime;
    flat.tnbWtnbRegistrationStartDateTime = data.importantDates.tnbWtnbRegistrationStartDateTime || data.tnbWtnbRegistrationStartDateTime;
    flat.openRegistrationStartDateTime = data.importantDates.openRegistrationStartDateTime || data.openRegistrationStartDateTime;
    flat.newPlayerOrientationDateTime = data.importantDates.newPlayerOrientationDateTime || data.newPlayerOrientationDateTime;
    flat.scoutNightDateTime = data.importantDates.scoutNightDateTime || data.scoutNightDateTime;
    flat.openingPartyDate = data.importantDates.openingPartyDate || data.openingPartyDate;
    flat.closingPartyDate = data.importantDates.closingPartyDate || data.closingPartyDate;
    flat.rainDate = data.importantDates.rainDate || data.rainDate;
    flat.offDatesCommaSeparated = data.importantDates.offDatesCommaSeparated || data.offDatesCommaSeparated;
    flat.offDates = data.importantDates.offDates || data.offDates;
  } else {
    flat.seasonStartDate = data.seasonStartDate;
    flat.seasonEndDate = data.seasonEndDate;
    flat.vetRegistrationStartDateTime = data.vetRegistrationStartDateTime;
    flat.tnbWtnbRegistrationStartDateTime = data.tnbWtnbRegistrationStartDateTime;
    flat.openRegistrationStartDateTime = data.openRegistrationStartDateTime;
    flat.newPlayerOrientationDateTime = data.newPlayerOrientationDateTime;
    flat.scoutNightDateTime = data.scoutNightDateTime;
    flat.openingPartyDate = data.openingPartyDate;
    flat.closingPartyDate = data.closingPartyDate;
    flat.rainDate = data.rainDate;
    flat.offDatesCommaSeparated = data.offDatesCommaSeparated;
    flat.offDates = data.offDates;
  }
  
  return flat;
}

/**
 * Main function to create Shopify product from a selected row
 * This is the entry point called from the menu
 */
export function createShopifyProductFromRow(sourceSheet, selectedRow) {
  const ui = SpreadsheetApp.getUi();

  // Read and parse the row data
  const parseResult = parseRowDataForProductCreation(sourceSheet, selectedRow);
  if (!parseResult || !parseResult.parsedData) {
    ui.alert('Failed to parse row data for product creation.');
    return;
  }

  const { parsedData, cellMapping, sourceSheet: sheet, rowNumber } = parseResult;

  // Validate that totalWeeks matches the actual span of seasonStartDate → seasonEndDate minus offDates
  const importantDates = parsedData.importantDates || parsedData;
  const totalWeeks = parsedData.inventoryInfo?.totalWeeks ?? parsedData.totalWeeks;
  const seasonStartDate = importantDates.seasonStartDate;
  const seasonEndDate = importantDates.seasonEndDate;
  const offDates = importantDates.offDates || [];

  if (totalWeeks != null && seasonStartDate instanceof Date && seasonEndDate instanceof Date) {
    const msPerWeek = 7 * 24 * 60 * 60 * 1000;
    const spanWeeks = Math.round((seasonEndDate - seasonStartDate) / msPerWeek) + 1;
    // Only count off dates that actually fall within the season span
    const offDatesInRange = offDates.filter(function(d) {
      return d instanceof Date && d >= seasonStartDate && d <= seasonEndDate;
    });
    const actualWeeks = spanWeeks - offDatesInRange.length;
    if (actualWeeks !== totalWeeks) {
      const openingPartyDate = importantDates.openingPartyDate;
      const closingPartyDate = importantDates.closingPartyDate;

      let suggestion = '';

      const openingSameAsStart = openingPartyDate instanceof Date && seasonStartDate instanceof Date &&
        openingPartyDate.getFullYear() === seasonStartDate.getFullYear() &&
        openingPartyDate.getMonth() === seasonStartDate.getMonth() &&
        openingPartyDate.getDate() === seasonStartDate.getDate();

      const closingSameAsEnd = closingPartyDate instanceof Date && seasonEndDate instanceof Date &&
        closingPartyDate.getFullYear() === seasonEndDate.getFullYear() &&
        closingPartyDate.getMonth() === seasonEndDate.getMonth() &&
        closingPartyDate.getDate() === seasonEndDate.getDate();

      if (openingSameAsStart) {
        suggestion += `\n• Opening Party (${openingPartyDate.toLocaleDateString()}) is on the Season Start date — if it's not a game week, move Season Start (col C) forward one week.`;
      }
      if (closingSameAsEnd) {
        suggestion += `\n• Closing Party (${closingPartyDate.toLocaleDateString()}) is on the Season End date — if it's not a game week, move Season End (col D) back one week.`;
      }

      ui.alert(
        '⚠️ Week Count Mismatch',
        `The season dates don't match "Total # of Weeks" in column B.\n\n` +
        `• Season Start (col C): ${seasonStartDate.toLocaleDateString()}\n` +
        `• Season End (col D): ${seasonEndDate.toLocaleDateString()}\n` +
        `• Off Dates: ${offDatesInRange.length} week(s) within season range\n` +
        `• Calculated weeks: ${actualWeeks} (${spanWeeks} span − ${offDatesInRange.length} off)\n` +
        `• Column B says: ${totalWeeks} weeks\n` +
        (suggestion ? `\nSuggestions:${suggestion}\n` : '') +
        `\nPlease fix columns B, C, or D before creating this product.`,
        ui.ButtonSet.OK
      );
      return;
    }
  }

  // Create the product directly — no pre-creation confirmation dialog
  try {
    // Flatten the data for Shopify API
    const flatData = flattenForShopifyAPI(parsedData);
    Logger.log(`About to send flattened data to Shopify: ${JSON.stringify(flatData, null, 2)}`);
    
    const result = createProductFromRowData(flatData);

    if (result.success) {
      writeProductCreationResults(sheet, rowNumber, result);
      const d = result.data;
      const variantLines = [
        d.veteranVariantGid  ? '• Veteran Registration' : null,
        d.earlyVariantGid    ? '• Early Registration'   : null,
        d.openVariantGid     ? '• Open Registration'    : null,
        d.waitlistVariantGid ? '• Waitlist Registration' : null,
      ].filter(Boolean).join('\n');
      ui.alert(`✅ Product created successfully!\n\nProduct URL: ${d.productUrl}\n\nVariants created:\n${variantLines || '(none recorded)'}`);
    } else {
      ui.alert(`❌ Product creation failed:\n\n${result.error}`);
      return result;
    }

  } catch (error) {
    Logger.log(`Error in createProductFromRowData: ${error}`);
    ui.alert('Error', `Failed to create product: ${error.message}`, ui.ButtonSet.OK);
  }
}
