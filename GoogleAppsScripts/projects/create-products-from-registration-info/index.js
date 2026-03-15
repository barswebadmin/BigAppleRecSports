/**
 * Unified Entry Point for Google Apps Script
 * All trigger functions and dependencies imported in dependency order
 */

// Tier 1: No dependencies (leaf nodes)
import * as secretsUtils from './src/shared-utilities/secretsUtils.js';
import * as textUtils from './src/helpers/textUtils.js';
import * as formatValidators from './src/helpers/formatValidators.js';
import * as constants from './src/config/constants.js';

// Tier 2: Depends on Tier 1
import * as normalizers from './src/helpers/normalizers.js';
import * as dateParsers from './src/helpers/dateParsers.js';
import * as formatting from './src/utils/formatting.js';

// Tier 3: Parsers (depend on Tier 1-2)
import * as parseLeagueBasicInfo from './src/parsers/parseLeagueBasicInfo.js';
import * as parseLeagueDetails from './src/parsers/parseLeagueDetails.js';
import * as parseSeasonDates from './src/parsers/parseSeasonDates.js';
import * as parsePrice from './src/parsers/parsePrice.js';
import * as parseLeagueTimes from './src/parsers/parseLeagueTimes.js';
import * as parseLocation from './src/parsers/parseLocation.js';
import * as parseRegistrationDates from './src/parsers/parseRegistrationDates.js';
import * as rowParser from './src/parsers/_rowParser.js';

// Tier 4: Data & Validation
import * as fieldValidation from './src/validators/fieldValidation.js';
import * as productDataProcessing from './src/data/productDataProcessing.js';
import * as cellMapping from './src/sheet/cellMapping.js';

// Tier 5: UI & Core Logic
import * as productCreationDialogs from './src/ui/productCreationDialogs.js';
import * as actionsSidebar from './src/ui/actionsSidebar.js';
import * as shopifyProductCreation from './src/core/portedFromProductCreateSheet/shopifyProductCreation.js';
import * as productCreationOrchestrator from './src/core/productCreationOrchestrator.js';
import * as instructions from './src/core/instructions.js';
import * as main from './src/core/main.js';

// Force esbuild to include all modules by referencing them
// This creates a side effect that prevents tree-shaking
globalThis.__KIRO_MODULES__ = {
  secretsUtils,
  textUtils,
  formatValidators,
  constants,
  normalizers,
  dateParsers,
  formatting,
  parseLeagueBasicInfo,
  parseLeagueDetails,
  parseSeasonDates,
  parsePrice,
  parseLeagueTimes,
  parseLocation,
  parseRegistrationDates,
  rowParser,
  fieldValidation,
  productDataProcessing,
  cellMapping,
  productCreationDialogs,
  actionsSidebar,
  shopifyProductCreation,
  productCreationOrchestrator,
  instructions,
  main
};

// Note: All trigger functions (onOpen, onEdit, showCreateProductPrompt)
// are declared in their respective files and will be available in global scope
// after esbuild removes the import/export statements

