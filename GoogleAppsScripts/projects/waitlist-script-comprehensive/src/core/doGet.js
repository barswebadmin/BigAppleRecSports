import { DEBUG_EMAIL } from '../config/constants';
import { getAllLeaguesForEmail } from '../shared-utilities/sheetUtils';
import { createErrorPage, createInteractiveSuccessPage } from '../ui/htmlPages';

/**
 * GET Handler for Interactive Waitlist Checker
 * Provides web interface for checking waitlist positions
 */

// biome-ignore lint/correctness/noUnusedVariables: GAS runtime trigger function
function doGet(e) {
  const debugInfo = [];
  
  try {
    debugInfo.push("🚀 doGet function called (Interactive Dropdown Version)");
    debugInfo.push(`📥 Parameters received: ${JSON.stringify(e.parameter)}`);
    debugInfo.push(`📥 ALL parameters: ${JSON.stringify(e, null, 2)}`);

    
    const email = e.parameter.email;
    const selectedLeague = e.parameter.league;
    
    debugInfo.push(`📧 Email: ${email}`);
    debugInfo.push(`🏆 Initially Selected League: ${selectedLeague}`);
    
    if (e.parameter.keys && !email) {
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
    debugInfo.push(`📍 Checking if SpreadsheetApp is available: ${typeof SpreadsheetApp !== 'undefined'}`);
    
    const result = getAllLeaguesForEmail(email);
    debugInfo.push("✅ getAllLeaguesForEmail returned successfully");
    debugInfo.push(...result.debugLog);
    
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
    debugInfo.push(`💥 Error in doGet: ${error.message}`);
    debugInfo.push(`📍 Error stack: ${error.stack}`);
    debugInfo.push(`📍 Error name: ${error.name}`);
    debugInfo.push(`📍 Error toString: ${error.toString()}`);
    
    // Try to get more context about where the error occurred
    if (error.stack) {
      const stackLines = error.stack.split('\n');
      debugInfo.push("📍 Stack trace:");
      stackLines.forEach(line => {
        debugInfo.push(`   ${line}`);
      });
    }
    MailApp.sendEmail({
      to: DEBUG_EMAIL,
      subject: `🔍 doGet Debug - ERROR: ${error.message}`,
      body: debugInfo.join('\n')
    });
    
    return createErrorPage("System Error",
      "An error occurred while checking your waitlist positions.",
      [`Error: ${error.message}`, `Stack: ${error.stack}`]);
  }
}

