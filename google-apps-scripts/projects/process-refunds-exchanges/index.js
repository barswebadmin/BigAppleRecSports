/**
 * Unused at the moment — this project's build.js bypasses esbuild and just
 * copies src/*.js into build/. See build.js for the rationale.
 *
 * Left in place so a future ESM-bundle refactor (adding `export` / `import`
 * across the src files) can be enabled by reverting build.js to delegate to
 * scripts/deployment/google/build.js, which uses this file as its entry point.
 */

import './src/doPost.js';
