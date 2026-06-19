#!/usr/bin/env deno run --allow-net --allow-env --allow-read

/**
 * Example of sending Slack messages using channel names in Deno
 */

// You'll need the Slack Web API SDK for Deno
// Add to your deno.json imports:
// "slack-web-api": "npm:@slack/web-api@^7.0.0"

interface SlackMessage {
  channel: string;  // Can be channel name (#general) or ID (C1234567890)
  text: string;
  blocks?: Record<string, unknown>[];
}

/**
 * Send message using channel name or ID
 */
async function sendSlackMessage(botToken: string, message: SlackMessage) {
  const { WebClient } = await import("npm:@slack/web-api@^7.0.0");

  const slack = new WebClient(botToken);

  try {
    // Slack Web API accepts both:
    // - Channel names: "#general", "general", "#random"
    // - Channel IDs: "C1234567890"
    const result = await slack.chat.postMessage({
      channel: message.channel,  // ← Works with names!
      text: message.text,
      blocks: message.blocks
    });

    console.log(`✅ Message sent to ${message.channel}`);
    return result;

  } catch (error) {
    console.error(`❌ Failed to send message to ${message.channel}:`, error);
    throw error;
  }
}

/**
 * Examples of different channel formats that work
 */
async function demonstrateChannelFormats() {
  const botToken = Deno.env.get("SLACK_BOT_TOKEN");

  if (!botToken) {
    console.error("❌ SLACK_BOT_TOKEN not found in environment");
    return;
  }

  console.log("📤 Testing different channel formats...\n");

  const testMessage = "Hello from Deno! 🦕";

  // All of these work:
  const channelFormats = [
    "#general",           // With hash
    "general",            // Without hash
    "#joe-test",          // With hash and hyphen
    "joe-test",           // Without hash, with hyphen
    // "C1234567890",     // Channel ID (if you have it)
  ];

  for (const channel of channelFormats) {
    try {
      await sendSlackMessage(botToken, {
        channel,
        text: `${testMessage} (sent to: ${channel})`
      });

      console.log(`✅ Successfully sent to: ${channel}`);
    } catch (error) {
      console.log(`❌ Failed to send to: ${channel} - ${error.message}`);
    }
  }
}

/**
 * Advanced: Send with blocks (rich formatting)
 */
async function sendRichMessage() {
  const botToken = Deno.env.get("SLACK_BOT_TOKEN");

  if (!botToken) return;

  await sendSlackMessage(botToken, {
    channel: "#joe-test",  // Using channel name!
    text: "Fallback text for notifications",
    blocks: [
      {
        type: "section",
        text: {
          type: "mrkdwn",
          text: "Hello from *Deno* 🦕\nSent to channel by name!"
        }
      },
      {
        type: "actions",
        elements: [
          {
            type: "button",
            text: {
              type: "plain_text",
              text: "Click Me"
            },
            value: "button_clicked"
          }
        ]
      }
    ]
  });
}

/**
 * Get channel info by name
 */
async function getChannelInfo(channelName: string) {
  const botToken = Deno.env.get("SLACK_BOT_TOKEN");
  if (!botToken) return;

  const { WebClient } = await import("npm:@slack/web-api@^7.0.0");
  const slack = new WebClient(botToken);

  try {
    // Get channel info - works with names too
    const result = await slack.conversations.info({
      channel: channelName  // Can use "#general" or "general"
    });

    console.log(`📋 Channel Info for ${channelName}:`);
    console.log(`  Name: #${result.channel?.name}`);
    console.log(`  ID: ${result.channel?.id}`);
    console.log(`  Purpose: ${result.channel?.purpose?.value || 'None'}`);
    console.log(`  Members: ${result.channel?.num_members || 'Unknown'}`);

    return result.channel;
  } catch (error) {
    console.error(`❌ Could not get info for ${channelName}:`, error.message);
  }
}

/**
 * Send DM to a user by username, email, or user ID
 */
async function sendDirectMessage(userIdentifier: string, messageText: string) {
  const botToken = Deno.env.get("SLACK_BOT_TOKEN");
  if (!botToken) return;

  const { WebClient } = await import("npm:@slack/web-api@^7.0.0");
  const slack = new WebClient(botToken);

  try {
    let userId = userIdentifier;

    // If not a user ID, look up the user
    if (!userIdentifier.startsWith('U')) {
      console.log(`🔍 Looking up user: ${userIdentifier}`);

      // Try to find user by email or username
      const userResult = await slack.users.lookupByEmail({
        email: userIdentifier
      }).catch(async () => {
        // If email lookup fails, try searching by username/display name
        const usersResult = await slack.users.list();
        const user = usersResult.members?.find(member =>
          member.name === userIdentifier ||
          member.profile?.display_name === userIdentifier ||
          member.real_name === userIdentifier
        );
        return user ? { user } : null;
      });

      if (!userResult?.user?.id) {
        throw new Error(`User not found: ${userIdentifier}`);
      }

      userId = userResult.user.id;
      console.log(`✅ Found user ID: ${userId} for ${userIdentifier}`);
    }

    // Open/create DM conversation
    const dmResult = await slack.conversations.open({
      users: userId
    });

    if (!dmResult.channel?.id) {
      throw new Error("Could not open DM conversation");
    }

    // Send message to the DM
    const result = await slack.chat.postMessage({
      channel: dmResult.channel.id,
      text: messageText
    });

    console.log(`✅ DM sent to ${userIdentifier} (${userId})`);
    return result;

  } catch (error) {
    console.error(`❌ Failed to send DM to ${userIdentifier}:`, error.message);
    throw error;
  }
}

/**
 * Examples of sending DMs
 */
async function demonstrateDirectMessages() {
  console.log("💬 Testing Direct Messages...\n");

  const testMessage = "Hello! This is a DM from Deno 🦕";

  // Different ways to specify users:
  const userIdentifiers = [
    "joe@bigapplerecsports.com",  // Email
    "joe",                        // Username
    "Joe Smith",                  // Display name
    // "U1234567890",             // User ID (if you have it)
  ];

  for (const userIdentifier of userIdentifiers) {
    try {
      await sendDirectMessage(userIdentifier, `${testMessage} (sent to: ${userIdentifier})`);
      console.log(`✅ Successfully sent DM to: ${userIdentifier}\n`);
    } catch (error) {
      console.log(`❌ Failed to send DM to: ${userIdentifier} - ${error.message}\n`);
    }
  }
}

// Example usage
if (import.meta.main) {
  console.log("🦕 Deno Slack Channel Messaging Examples\n");

  // Test different channel formats
  await demonstrateChannelFormats();

  console.log("\n📋 Getting channel info...");
  await getChannelInfo("#joe-test");

  console.log("\n📤 Sending rich message...");
  await sendRichMessage();

  console.log("\n💬 Testing Direct Messages...");
  await demonstrateDirectMessages();
}