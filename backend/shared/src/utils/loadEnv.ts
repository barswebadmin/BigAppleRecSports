import * as path from "node:path";
import * as dotenv from "dotenv";
import { fileURLToPath } from "node:url";
import fs from "node:fs";

/**
 * Loads the root-level .env file once, relative to the location of this utility.
 * Can be safely called from any package without duplication.
 */
export function loadEnv() {
  const __dirname = path.dirname(fileURLToPath(import.meta.url));

  // Traverse up to the monorepo root (adjust as needed)
  const envPath = path.resolve(__dirname, "../../../.env");

  if (!fs.existsSync(envPath)) {
    console.warn(`⚠️  .env file not found at expected path: ${envPath}`);
    return;
  }

  dotenv.config({ path: envPath });
}