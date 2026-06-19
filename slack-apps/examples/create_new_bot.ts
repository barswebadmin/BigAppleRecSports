#!/usr/bin/env deno run --allow-read --allow-write

/**
 * Script to create a new Slack bot that uses shared authentication
 * Usage: deno run --allow-read --allow-write scripts/create_new_bot.ts <bot-name>
 */

async function createNewBot(botName: string) {
  const botDir = `${botName}-bot`;

  console.log(`🤖 Creating new Slack bot: ${botName}-bot`);

  // Create bot directory
  await Deno.mkdir(botDir, { recursive: true });

  // Create deno.json with shared imports
  const denoConfig = {
    compilerOptions: {
      allowJs: true,
      lib: ["deno.window"],
      strict: true
    },
    imports: {
      "firebase-admin/app": "npm:firebase-admin@^12.0.0/app",
      "firebase-admin/firestore": "npm:firebase-admin@^12.0.0/firestore",
      "googleapis": "npm:googleapis@^128.0.0",
      "google-auth-library": "npm:google-auth-library@^9.0.0",
      "deno-slack-sdk/mod.ts": "https://deno.land/x/deno_slack_sdk@2.9.0/mod.ts",
      "deno-slack-api/mod.ts": "https://deno.land/x/deno_slack_api@2.5.2/mod.ts",
      "@bars/shared/": "../shared/",
      "@bars/google": "../shared/google_client.ts",
      "@bars/firebase": "../shared/firebase_client.ts"
    },
    tasks: {
      dev: "deno run --allow-net --allow-read --allow-env --allow-write main.ts",
      start: "slack run",
      test: "deno test --allow-net --allow-read --allow-env",
      "test-auth": "deno run --allow-net --allow-env --allow-read test_auth.ts"
    },
    exclude: ["node_modules"]
  };

  await Deno.writeTextFile(
    `${botDir}/deno.json`,
    JSON.stringify(denoConfig, null, 2)
  );

  // Create basic test_auth.ts
  const testAuth = `#!/usr/bin/env deno run --allow-net --allow-env --allow-read

import { firebaseClient } from "@bars/firebase";
import { googleClient } from "@bars/google";
import { getAdminUserEmail } from "@bars/shared/config/environment.ts";

/**
 * Test script for ${botName}-bot using shared authentication
 */

async function testAuth() {
  console.log("🧪 Testing ${botName}-bot authentication...");

  try {
    // Test Firebase connection with ${botName} collection
    const testData = {
      test_id: crypto.randomUUID(),
      bot_name: "${botName}-bot",
      created_at: new Date(),
    };

    const docId = await firebaseClient.addDoc("${botName}_test", testData);
    console.log(\`  ✅ Firebase: Test document created (\${docId})\`);

    // Test Google APIs
    const adminEmail = getAdminUserEmail();
    await googleClient.sheets(adminEmail);
    console.log(\`  ✅ Google Sheets API: Connected successfully\`);

    // Cleanup
    await firebaseClient.deleteDoc("${botName}_test", docId);
    console.log(\`  ✅ Cleanup: Test document deleted\`);

    console.log("🎉 ${botName}-bot authentication test passed!");
  } catch (error) {
    console.error(\`❌ ${botName}-bot authentication test failed: \${error.message}\`);
    Deno.exit(1);
  }
}

if (import.meta.main) {
  await testAuth();
}`;

  await Deno.writeTextFile(`${botDir}/test_auth.ts`, testAuth);

  // Create example function directory
  await Deno.mkdir(`${botDir}/functions/${botName}`, { recursive: true });

  // Create example function
  const exampleFunction = `import { DefineFunction, Schema, SlackFunction } from "deno-slack-sdk/mod.ts";
import { firebaseClient } from "@bars/firebase";
import { googleClient } from "@bars/google";
import { getAdminUserEmail } from "@bars/shared/config/environment.ts";

/**
 * Example ${botName} bot function demonstrating shared Firebase + Google API integration
 */
export const Example${botName.charAt(0).toUpperCase() + botName.slice(1)}Function = DefineFunction({
  callback_id: "example_${botName}",
  title: "Example ${botName.charAt(0).toUpperCase() + botName.slice(1)} Function",
  description: "Demonstrates shared Firebase and Google API integration for ${botName}",
  source_file: "functions/${botName}/example_function.ts",
  input_parameters: {
    properties: {
      message: {
        type: Schema.types.string,
        description: "Test message for ${botName} bot",
      },
    },
    required: ["message"],
  },
  output_parameters: {
    properties: {
      result: {
        type: Schema.types.string,
        description: "Result message",
      },
    },
    required: ["result"],
  },
});

export default SlackFunction(
  Example${botName.charAt(0).toUpperCase() + botName.slice(1)}Function,
  async ({ inputs }) => {
    try {
      const { message } = inputs;
      const adminEmail = getAdminUserEmail();

      // Store data in Firestore using shared client
      const data = {
        message,
        bot_name: "${botName}-bot",
        created_at: new Date(),
      };

      const docId = await firebaseClient.addDoc("${botName}_data", data);
      console.log(\`Stored data with ID: \${docId}\`);

      return {
        outputs: {
          result: \`✅ ${botName.charAt(0).toUpperCase() + botName.slice(1)} bot processed: "\${message}" (ID: \${docId})\`,
        },
      };

    } catch (error) {
      console.error("Error in ${botName} function:", error);

      return {
        error: \`Failed to process ${botName} request: \${error.message}\`,
      };
    }
  }
);`;

  await Deno.writeTextFile(`${botDir}/functions/${botName}/example_function.ts`, exampleFunction);

  // Create README
  const readme = `# ${botName.charAt(0).toUpperCase() + botName.slice(1)} Bot

A Slack bot for Big Apple Rec Sports ${botName} functionality.

## Setup

This bot uses shared authentication from \`../shared/\`. No additional credential setup required!

## Testing

\`\`\`bash
# Test shared authentication
deno run test-auth

# Or use the root shared test
cd .. && deno run --allow-net --allow-env --allow-read test_shared_auth.ts
\`\`\`

## Development

\`\`\`bash
slack run
\`\`\`

## Using Shared Services

\`\`\`typescript
import { firebaseClient } from "@bars/firebase";
import { googleClient } from "@bars/google";
import { getAdminUserEmail } from "@bars/shared/config/environment.ts";

// Firebase operations
await firebaseClient.addDoc("${botName}_collection", data);

// Google API operations
const sheets = await googleClient.sheets(getAdminUserEmail());
\`\`\`

## Collections Used

- \`${botName}_data\`: Main data for ${botName} operations
- \`${botName}_logs\`: Activity logs
- \`${botName}_config\`: Bot configuration

All collections are shared across the BARS ecosystem via Firebase.`;

  await Deno.writeTextFile(`${botDir}/README.md`, readme);

  console.log(`✅ Created ${botName}-bot with shared authentication!`);
  console.log(`\n📁 Files created:`);
  console.log(`  - ${botDir}/deno.json`);
  console.log(`  - ${botDir}/test_auth.ts`);
  console.log(`  - ${botDir}/functions/${botName}/example_function.ts`);
  console.log(`  - ${botDir}/README.md`);
  console.log(`\n🚀 Next steps:`);
  console.log(`  1. cd ${botDir}`);
  console.log(`  2. deno run test-auth`);
  console.log(`  3. slack create ${botName}-app --template=blank`);
  console.log(`  4. slack run`);
  console.log(`\n✨ Your new bot will automatically use the same credentials as all other BARS bots!`);
}

if (import.meta.main) {
  const botName = Deno.args[0];

  if (!botName) {
    console.error("❌ Please provide a bot name:");
    console.error("  Usage: deno run --allow-read --allow-write scripts/create_new_bot.ts <bot-name>");
    console.error("  Example: deno run --allow-read --allow-write scripts/create_new_bot.ts referee");
    Deno.exit(1);
  }

  await createNewBot(botName);
}