/**
 * HTML Page Generation for Interactive Waitlist Checker
 * Generates styled HTML pages for the web app
 */

/**
 * Create error page HTML
 * @param {string} title - Error title
 * @param {string} message - Error message
 * @param {Array<string>} details - Optional details array
 * @returns {HtmlOutput} - HTML page
 */
export function createErrorPage(title, message, details = []) {
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
                margin: 10px 0;
                color: #666;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🏳️‍🌈 BARS Waitlist</h1>
            </div>
            <div class="content">
                <div class="error-icon">❌</div>
                <h2>${title}</h2>
                <div class="message">${message}</div>
                ${detailsHtml}
            </div>
        </div>
    </body>
    </html>
  `);
}

/**
 * Create interactive success page with dropdown for multiple leagues
 * @param {Array<Object>} leagues - Array of {league, spot} objects
 * @param {string} email - User's email
 * @param {string} selectedLeague - Initially selected league (optional)
 * @returns {HtmlOutput} - HTML page
 */
export function createInteractiveSuccessPage(leagues, email, selectedLeague) {
  if (!leagues || leagues.length === 0) {
    return createErrorPage("Not Found", "No waitlist positions found for this email.");
  }
  
  const initialLeague = selectedLeague || leagues[0].league;
  const initialSpot = leagues.find(l => l.league === initialLeague)?.spot || leagues[0].spot;
  
  const leagueOptions = leagues
    .map(l => `<option value="${escapeHtml(l.league)}" ${l.league === initialLeague ? 'selected' : ''}>${escapeHtml(l.league)}</option>`)
    .join('');
  
  const leagueDataJson = JSON.stringify(leagues.map(l => ({
    league: l.league,
    spot: l.spot
  })));
  
  return HtmlService.createHtmlOutput(`
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Your Waitlist Position - BARS</title>
        <style>
            body {
                margin: 0;
                padding: 20px;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #4CAF50 0%, #2e7d32 100%);
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
                background: linear-gradient(135deg, #4CAF50 0%, #2e7d32 100%);
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
                padding: 40px 30px;
            }
            .success-icon {
                font-size: 5em;
                text-align: center;
                margin-bottom: 20px;
            }
            .greeting {
                font-size: 1.3em;
                text-align: center;
                color: #333;
                margin-bottom: 30px;
            }
            .league-selector {
                margin: 30px 0;
            }
            .league-selector label {
                display: block;
                font-weight: 600;
                color: #555;
                margin-bottom: 10px;
                font-size: 1.1em;
            }
            .league-selector select {
                width: 100%;
                padding: 15px;
                font-size: 1em;
                border: 2px solid #4CAF50;
                border-radius: 10px;
                background: white;
                cursor: pointer;
                transition: all 0.3s;
            }
            .league-selector select:hover {
                border-color: #2e7d32;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }
            .position-display {
                background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%);
                padding: 30px;
                border-radius: 15px;
                text-align: center;
                margin: 30px 0;
                border: 3px solid #4CAF50;
            }
            .position-number {
                font-size: 4em;
                font-weight: 700;
                color: #2e7d32;
                margin: 10px 0;
            }
            .position-text {
                font-size: 1.4em;
                color: #1b5e20;
                margin: 10px 0;
            }
            .info-box {
                background: #fff3cd;
                border: 2px solid #ffc107;
                border-radius: 10px;
                padding: 20px;
                margin: 20px 0;
            }
            .info-box p {
                margin: 10px 0;
                color: #856404;
                line-height: 1.6;
            }
            .footer {
                text-align: center;
                padding: 20px;
                color: #666;
                border-top: 1px solid #ddd;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🏳️‍🌈 BARS Waitlist</h1>
            </div>
            <div class="content">
                <div class="success-icon">✅</div>
                <div class="greeting">
                    You're on the waitlist${leagues.length > 1 ? ' for <strong><u>' + leagues.length + '</u></strong> leagues' : ''}
                </div>
                
                ${leagues.length > 1 ? `
                <div class="league-selector">
                    <label for="league-select">Select a league to view your position:</label>
                    <select id="league-select">
                        ${leagueOptions}
                    </select>
                </div>
                ` : ''}
                
                <div class="position-display">
                    <div class="position-text">Your position:</div>
                    <div class="position-number" id="position-number">#${initialSpot}</div>
                    <div class="position-text" id="league-name">${escapeHtml(initialLeague)}</div>
                </div>
                
                <div class="info-box">
                    <p><strong>📧 We'll reach out via email</strong> when a spot opens up!</p>
                    <p>Keep an eye on your inbox (${escapeHtml(email)}) for updates from our league leadership.</p>
                </div>
            </div>
            <div class="footer">
                <p><strong>Big Apple Rec Sports</strong></p>
                <p>Follow us: <a href="https://www.instagram.com/bigapplerecsports/">Instagram</a> | <a href="https://www.facebook.com/groups/bigapplerecsports">Facebook</a></p>
            </div>
        </div>
        
        <script>
            const leagueData = ${leagueDataJson};
            const leagueSelect = document.getElementById('league-select');
            const positionNumber = document.getElementById('position-number');
            const leagueName = document.getElementById('league-name');
            
            if (leagueSelect) {
                leagueSelect.addEventListener('change', function() {
                    const selectedLeague = this.value;
                    const leagueInfo = leagueData.find(l => l.league === selectedLeague);
                    
                    if (leagueInfo) {
                        positionNumber.textContent = '#' + leagueInfo.spot;
                        leagueName.textContent = leagueInfo.league;
                    }
                });
            }
        </script>
    </body>
    </html>
  `);
}

/**
 * Escape HTML special characters
 * @param {string} text - Text to escape
 * @returns {string} - Escaped text
 */
function escapeHtml(text) {
  if (!text) return '';
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

