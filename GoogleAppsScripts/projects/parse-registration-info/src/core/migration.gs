/**
 * Migration logic for parse-registration-info
 * Handles the actual data transfer to target spreadsheet
 *
 * @fileoverview Migration workflow and data transfer
 * @requires ../config/constants.gs
 * @requires ../validators/fieldValidation.gs
 * @requires ../helpers/textUtils.gs
 * @requires ../parsers/_rowParser.gs
 */

// Import references for editor support
/// <reference path="../config/constants.gs" />
/// <reference path="../validators/fieldValidation.gs" />
/// <reference path="../helpers/textUtils.gs" />
/// <reference path="../parsers/_rowParser.gs" />

// migrateRowToTarget_ function removed - only creating products from this sheet, not migrating them
// Helper functions like parseSourceRowEnhanced_, buildFuzzyHeaderIndex_, checkRequiredFields_,
// getTargetIndexMap_, and makeKey_ are preserved in their respective files for potential use in product creation
