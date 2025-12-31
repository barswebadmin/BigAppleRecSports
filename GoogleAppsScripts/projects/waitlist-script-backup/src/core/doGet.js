/**
 * GET Handler for Interactive Waitlist Checker
 * Provides web interface for checking waitlist positions
 */

function doGet(e) {
  let debugInfo = [];
  
  try {
    debugInfo.push("🚀 doGet function called (Interactive Dropdown Version)");
    debugInfo.push("📥 Parameters received: " + JSON.stringify(e.parameter));
    debugInfo.push("📥 ALL parameters: " + JSON.stringify(e, null, 2));
    
    // Send immediate email to confirm doGet was called
    try {
      MailApp.sendEmail({
        to: DEBUG_EMAIL,
        subject: "🔍 doGet STARTED",
        body: debugInfo.join('\n')
      });
    } catch (mailError) {
      debugInfo.push("⚠️ Could not send startup email: " + mailError.message);
    }
    
    const email = e.parameter.email;
    const selectedLeague = e.parameter.league;
    
    debugInfo.push(`📧 Email: ${email}`);
    debugInfo.push(`🏆 Initially Selected League: ${selectedLeague}`);
    
    if (!email) {
      debugInfo.push("❌ Missing email parameter");
      
      MailApp.sendEmail({
        to: DEBUG_EMAIL,
        subject: "🔍 doGet Debug - Missing Email",
        body: debugInfo.join('\n')
      });
      
      return createErrorPage("Missing Information",
        "Email address is required to check waitlist positions.");
    }
    
    debugInfo.push("🔍 About to call getAllLeaguesForEmail...");
    debugInfo.push("📍 Checking if getSheet function is available...");
    debugInfo.push("📍 Checking if SpreadsheetApp is available: " + (typeof SpreadsheetApp !== 'undefined'));
    
    const result = getAllLeaguesForEmail(email);
    debugInfo.push("✅ getAllLeaguesForEmail returned successfully");
    debugInfo.push(...result.debugLog);
    
    if (result.error) {
      debugInfo.push(`❌ Error getting leagues: ${result.error}`);
      
      MailApp.sendEmail({
        to: DEBUG_EMAIL,
        subject: "🔍 doGet Debug - Error Getting Leagues",
        body: debugInfo.join('\n')
      });
      
      return createErrorPage("System Error",
        `An error occurred: ${result.error}`);
    }
    
    if (!result.leagues || result.leagues.length === 0) {
      debugInfo.push("❌ No leagues found for this email");
      
      MailApp.sendEmail({
        to: DEBUG_EMAIL,
        subject: "🔍 doGet Debug - No Leagues Found",
        body: debugInfo.join('\n')
      });
      
      return createErrorPage("Not Found",
        "We couldn't find any waitlist submissions for this email address.",
        [`Email: ${email}`]);
    }
    
    debugInfo.push(`✅ Found ${result.leagues.length} leagues for email`);
    result.leagues.forEach(league => {
      debugInfo.push(`   - ${league.league}: Position #${league.spot}`);
    });
    
    return createInteractiveSuccessPage(result.leagues, email, selectedLeague);
    
  } catch (error) {
    debugInfo.push("💥 Error in doGet: " + error.message);
    debugInfo.push("📍 Error stack: " + error.stack);
    debugInfo.push("📍 Error name: " + error.name);
    debugInfo.push("📍 Error toString: " + error.toString());
    
    // Try to get more context about where the error occurred
    if (error.stack) {
      const stackLines = error.stack.split('\n');
      debugInfo.push("📍 Stack trace:");
      stackLines.forEach(line => debugInfo.push("   " + line));
    }
    
    try {
      MailApp.sendEmail({
        to: DEBUG_EMAIL,
        subject: "🔍 doGet Debug - ERROR: " + error.message,
        body: debugInfo.join('\n')
      });
    } catch (mailError) {
      // If we can't even send email, there's nothing we can do
    }
    
    return createErrorPage("System Error",
      "An error occurred while checking your waitlist positions.",
      [`Error: ${error.message}`, `Stack: ${error.stack}`]);
  }
}

