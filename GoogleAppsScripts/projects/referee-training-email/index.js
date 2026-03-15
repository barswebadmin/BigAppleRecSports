/**
 * Entry point for referee-training-email GAS project.
 * Files imported in dependency order so globals are defined before use.
 */

// Tier 1: config (no dependencies)
import * as config from './src/config.js';

// Tier 2: calendar + email (depend on config globals)
import * as calendar from './src/calendar.js';
import * as email from './src/email.js';

// Tier 3: trigger (depends on calendar + email + sendToLambda)
import * as trigger from './src/trigger.js';
import * as sendToLambda from './src/sendToLambda.js';

// Prevent tree-shaking — all globals must survive bundling
globalThis.__KIRO_MODULES__ = { config, calendar, email, trigger, sendToLambda };

// Note: onFormSubmit (trigger.js) is the active trigger.
// sendToLambda (sendToLambda.js) fires after calendar + email work completes.
