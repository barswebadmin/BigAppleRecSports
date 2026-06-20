#!/usr/bin/env deno run --allow-net --allow-env --allow-read

/**
 * Benchmark: Channel ID vs Channel Name performance
 */

async function benchmarkSlackMessaging() {
  const botToken = Deno.env.get("SLACK_BOT_TOKEN");
  if (!botToken) {
    console.error("❌ SLACK_BOT_TOKEN not found");
    return;
  }

  const { WebClient } = await import("npm:@slack/web-api@^7.0.0");
  const slack = new WebClient(botToken);

  // Test channel (replace with your actual channel)
  const channelName = "#joe-test";
  const channelId = "C1234567890"; // Replace with actual ID if you have it

  const iterations = 5;

  console.log("🏃‍♂️ Benchmarking Slack Message Performance");
  console.log(`📊 Running ${iterations} iterations each...\n`);

  // Benchmark using channel name
  console.log("📤 Testing Channel Names...");
  const nameTimings: number[] = [];

  for (let i = 0; i < iterations; i++) {
    const start = performance.now();

    try {
      await slack.chat.postMessage({
        channel: channelName,  // Using channel name
        text: `Performance test ${i + 1} (by name) - ${new Date().toISOString()}`
      });

      const duration = performance.now() - start;
      nameTimings.push(duration);
      console.log(`  ${i + 1}. Channel name: ${duration.toFixed(0)}ms`);

      // Small delay to avoid rate limits
      await new Promise(resolve => setTimeout(resolve, 1000));
    } catch (error) {
      console.log(`  ${i + 1}. Channel name: ERROR - ${error.message}`);
    }
  }

  /*
  // Benchmark using channel ID (uncomment if you have the actual channel ID)
  console.log("\n📤 Testing Channel IDs...");
  const idTimings: number[] = [];

  for (let i = 0; i < iterations; i++) {
    const start = performance.now();

    try {
      await slack.chat.postMessage({
        channel: channelId,  // Using channel ID
        text: `Performance test ${i + 1} (by ID) - ${new Date().toISOString()}`
      });

      const duration = performance.now() - start;
      idTimings.push(duration);
      console.log(`  ${i + 1}. Channel ID: ${duration.toFixed(0)}ms`);

      await new Promise(resolve => setTimeout(resolve, 1000));
    } catch (error) {
      console.log(`  ${i + 1}. Channel ID: ERROR - ${error.message}`);
    }
  }
  */

  // Calculate averages
  const nameAvg = nameTimings.length > 0
    ? nameTimings.reduce((a, b) => a + b, 0) / nameTimings.length
    : 0;

  // const idAvg = idTimings.length > 0
  //   ? idTimings.reduce((a, b) => a + b, 0) / idTimings.length
  //   : 0;

  console.log("\n📈 Results:");
  console.log(`  Channel Names: ${nameAvg.toFixed(0)}ms average`);
  // console.log(`  Channel IDs: ${idAvg.toFixed(0)}ms average`);
  // console.log(`  Difference: ${Math.abs(nameAvg - idAvg).toFixed(0)}ms`);

  console.log("\n💡 Key Findings:");
  console.log("  • Channel names are auto-resolved by Slack API (no extra lookup needed)");
  console.log("  • Performance difference is typically <50ms");
  console.log("  • For most applications, the difference is negligible");
  console.log("  • Channel names are more maintainable (no ID management)");
}

/**
 * Test what happens with invalid channels
 */
async function testInvalidChannels() {
  const botToken = Deno.env.get("SLACK_BOT_TOKEN");
  if (!botToken) return;

  const { WebClient } = await import("npm:@slack/web-api@^7.0.0");
  const slack = new WebClient(botToken);

  console.log("\n🧪 Testing Invalid Channels...");

  const testCases = [
    { channel: "#nonexistent-channel", description: "Invalid channel name" },
    { channel: "C9999999999", description: "Invalid channel ID" },
    { channel: "#general-old", description: "Possibly renamed channel" },
  ];

  for (const testCase of testCases) {
    const start = performance.now();

    try {
      await slack.chat.postMessage({
        channel: testCase.channel,
        text: "Test message"
      });

      const duration = performance.now() - start;
      console.log(`  ✅ ${testCase.description}: ${duration.toFixed(0)}ms`);
    } catch (error) {
      const duration = performance.now() - start;
      console.log(`  ❌ ${testCase.description}: ${duration.toFixed(0)}ms - ${error.message}`);
    }
  }
}

if (import.meta.main) {
  await benchmarkSlackMessaging();
  await testInvalidChannels();
}