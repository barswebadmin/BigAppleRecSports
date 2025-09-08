function doGet(e) {
  let debugInfo = [];
  
  try {
    debugInfo.push("🚀 doGet function called (Interactive Dropdown Version)");
    debugInfo.push("📥 Parameters received: " + JSON.stringify(e.parameter));
    
    // Extract parameters
    const email = e.parameter.email;
    const selectedLeague = e.parameter.league; // This might be the initially selected league
    
    debugInfo.push(`📧 Email: ${email}`);
    debugInfo.push(`🏆 Initially Selected League: ${selectedLeague}`);
    
    // Validate email parameter
    if (!email) {
      debugInfo.push("❌ Missing email parameter");
      
      MailApp.sendEmail({
        to: "jdazz87@gmail.com",
        subject: "🔍 doGet Debug - Missing Email",
        body: debugInfo.join('\n')
      });
      
      return createErrorPage("Missing Information", 
        "Email address is required to check waitlist positions.");
    }
    
    debugInfo.push("🔍 Calling getAllLeaguesForEmail...");
    
    // Get all leagues for this email
    const result = getAllLeaguesForEmail(email);
    debugInfo.push(...result.debugLog);
    
    if (result.error) {
      debugInfo.push(`❌ Error getting leagues: ${result.error}`);
      
      MailApp.sendEmail({
        to: "jdazz87@gmail.com",
        subject: "🔍 doGet Debug - Error Getting Leagues",
        body: debugInfo.join('\n')
      });
      
      return createErrorPage("System Error", 
        `An error occurred: ${result.error}`);
    }
    
    if (!result.leagues || result.leagues.length === 0) {
      debugInfo.push("❌ No leagues found for this email");
      
      MailApp.sendEmail({
        to: "jdazz87@gmail.com",
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
    
    // Create interactive success page with dropdown
    return createInteractiveSuccessPage(result.leagues, email, selectedLeague);
    
  } catch (error) {
    debugInfo.push("💥 Error in doGet: " + error.message);
    debugInfo.push("📍 Error stack: " + error.stack);
    
    MailApp.sendEmail({
      to: "jdazz87@gmail.com",
      subject: "🔍 doGet Debug - ERROR",
      body: debugInfo.join('\n')
    });
    
    return createErrorPage("System Error",
      "An error occurred while checking your waitlist positions.",
      [`Error: ${error.message}`]);
  }
}



function createErrorPage(title, message, details = []) {
  const detailsHtml = details.length > 0 ? 
    `<div class="details"><ul>${details.map(d => `<li>${d}</li>`).join('')}</ul></div>` : '';
     
  return HtmlService.createHtmlOutput(`
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Waitlist Check - BARS</title>
        <style>
            body {
                margin: 0;
                padding: 20px;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #ff7043 0%, #ff5722 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .container {
                max-width: 600px;
                background: white;
                border-radius: 20px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                overflow: hidden;
            }
            .header {
                background: linear-gradient(135deg, #f44336 0%, #d32f2f 100%);
                color: white;
                padding: 30px;
                text-align: center;
            }
            .header h1 {
                margin: 0;
                font-size: 2.2em;
                font-weight: 600;
            }
            .content {
                padding: 30px;
                text-align: center;
            }
            .error-icon {
                font-size: 4em;
                margin-bottom: 20px;
                color: #f44336;
            }
            .message {
                font-size: 1.2em;
                color: #555;
                margin: 20px 0;
                line-height: 1.5;
            }
            .details {
                background: #f5f5f5;
                padding: 20px;
                border-radius: 10px;
                margin: 20px 0;
                text-align: left;
            }
            .details ul {
                margin: 0;
                padding-left: 20px;
            }
            .details li {
                margin: 8px 0;
                color: #666;
            }
            .footer {
                background: #d32f2f;
                color: white;
                padding: 20px 30px;
                text-align: center;
            }
            .footer a {
                color: #ffcdd2;
                text-decoration: none;
                font-weight: 600;
                padding: 10px 20px;
                background: rgba(255,255,255,0.1);
                border-radius: 5px;
                display: inline-block;
                margin-top: 10px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>⚠️ ${title}</h1>
            </div>
            <div class="content">
                <div class="error-icon">❌</div>
                <div class="message">${message}</div>
                ${detailsHtml}
            </div>
            <div class="footer">
                <p>Need help? Contact our support team:</p>
                <a href="mailto:info@bigapplerecsports.com">📧 Contact Support</a>
            </div>
        </div>
    </body>
    </html>
  `);
}
function createInteractiveSuccessPage(leagues, email, selectedLeague) {
  // Sort leagues alphabetically
  leagues.sort((a, b) => a.league.localeCompare(b.league));
  
  // Determine which league to show initially
  let initialLeague = leagues[0];
  if (selectedLeague) {
    const found = leagues.find(l => l.league.toLowerCase() === selectedLeague.toLowerCase());
    if (found) initialLeague = found;
  }
  
  // Generate options HTML
  const optionsHtml = leagues.map(league => 
    `<option value="${league.league}" data-spot="${league.spot}" ${league.league === initialLeague.league ? 'selected' : ''}>${league.league}</option>`
  ).join('');
  
  return HtmlService.createHtmlOutput(`
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Your Waitlist Positions - BARS</title>
        <style>
            body {
                margin: 0;
                padding: 20px;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .container {
                max-width: 700px;
                background: white;
                border-radius: 20px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                overflow: hidden;
            }
            .header {
                background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
                color: white;
                padding: 30px;
                text-align: center;
            }
            .header h1 {
                margin: 0;
                font-size: 2.2em;
                font-weight: 600;
            }
            .selector-section {
                padding: 30px;
                background: #f8fffe;
                border-bottom: 1px solid #e0e0e0;
            }
            .league-selector {
                width: 100%;
                padding: 15px;
                font-size: 1.1em;
                border: 2px solid #4CAF50;
                border-radius: 10px;
                background: white;
                margin-bottom: 20px;
            }
            .league-selector:focus {
                outline: none;
                border-color: #45a049;
                box-shadow: 0 0 10px rgba(76, 175, 80, 0.3);
            }
            .position-display {
                text-align: center;
                padding: 40px 30px;
                background: #f8fffe;
            }
            .position-circle {
                width: 120px;
                height: 120px;
                background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
                color: white;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 2.5em;
                font-weight: bold;
                margin: 0 auto 20px;
                box-shadow: 0 5px 15px rgba(76, 175, 80, 0.3);
                transition: all 0.3s ease;
            }
            .position-text {
                font-size: 1.4em;
                color: #2e7d32;
                margin: 20px 0;
                font-weight: 500;
            }
            .current-league {
                font-size: 1.2em;
                color: #333;
                margin: 15px 0;
                font-weight: 600;
            }
            .details {
                background: #f5f5f5;
                padding: 25px 30px;
                border-top: 1px solid #e0e0e0;
            }
            .detail-item {
                margin: 12px 0;
                color: #555;
                font-size: 1.1em;
            }
            .detail-label {
                font-weight: 600;
                color: #333;
            }
            .footer {
                background: #2e7d32;
                color: white;
                padding: 20px 30px;
                text-align: center;
                font-size: 0.95em;
            }
            .footer a {
                color: #81c784;
                text-decoration: none;
            }
            .league-count {
                background: #e8f5e8;
                padding: 15px;
                border-radius: 10px;
                margin-bottom: 20px;
                text-align: center;
                color: #2e7d32;
                font-weight: 600;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎉 Your Waitlist Positions</h1>
            </div>
            
            <div class="selector-section">
                <div class="league-count">
                    📊 You're on the waitlist for ${leagues.length} league${leagues.length > 1 ? 's' : ''}
                </div>
                <label for="leagueSelector" style="font-weight: 600; color: #333; display: block; margin-bottom: 10px;">
                    🏆 Select a league to view your position:
                </label>
                <select id="leagueSelector" class="league-selector">
                    ${optionsHtml}
                </select>
            </div>
            
            <div class="position-display">
                <div class="position-circle" id="positionCircle">#${initialLeague.spot}</div>
                <div class="current-league" id="currentLeague">${initialLeague.league}</div>
                <div class="position-text" id="positionText">
                    You are <strong>#${initialLeague.spot}</strong> on the waitlist
                </div>
                <p style="color: #666; margin-top: 20px;">
                    📧 We'll reach out if a spot opens up!
                </p>
            </div>
            
            <div class="details">
                <div class="detail-item">
                    <span class="detail-label">📧 Email:</span> ${email}
                </div>
                <div class="detail-item">
                    <span class="detail-label">⏰ Checked:</span> ${new Date().toLocaleString()}
                </div>
            </div>
            
            <div class="footer">
                <p>
                    🍎 <strong>Big Apple Recreational Sports</strong><br>
                    Questions? Email us at <a href="mailto:info@bigapplerecsports.com">info@bigapplerecsports.com</a>
                </p>
            </div>
        </div>

        <script>
            const selector = document.getElementById('leagueSelector');
            const positionCircle = document.getElementById('positionCircle');
            const currentLeague = document.getElementById('currentLeague');
            const positionText = document.getElementById('positionText');
            
            selector.addEventListener('change', function() {
                const selectedOption = this.options[this.selectedIndex];
                const spot = selectedOption.getAttribute('data-spot');
                const league = selectedOption.value;
                
                // Update display with animation
                positionCircle.style.transform = 'scale(0.8)';
                
                setTimeout(() => {
                    positionCircle.textContent = '#' + spot;
                    currentLeague.textContent = league;
                    positionText.innerHTML = \`You are <strong>#\${spot}</strong> on the waitlist\`;
                    positionCircle.style.transform = 'scale(1)';
                }, 150);
            });
        </script>
    </body>
    </html>
  `);
}
