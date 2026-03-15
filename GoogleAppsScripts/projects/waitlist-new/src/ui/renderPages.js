/**
 * Page rendering service
 * Handles rendering complete HTML pages, responses, and error handling for waitlist operations
 */

import { detectMobileFromSource, generateAllStyles } from './generateStyles.js';

export class PageRender {

  /**
   * Escape HTML special characters to prevent syntax errors
   * @param {string} str - String to escape
   * @returns {string} Escaped string
   */
  escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  /**
   * Render waitlist positions page
   * @param {Array} waitlistPositionsForPlayer - Array of position objects for the player
   * @param {string} productId - Product ID (so renderer knows which one to render first)
   * @param {string} source - Source of request (shopify, etc.)
   * @returns {GoogleAppsScript.HTML.HtmlOutput} HTML output
   */
  renderPositionsPage(waitlistPositionsForPlayer, productId, source) {
    const isMobile = detectMobileFromSource(source);

    // Find the current product and other positions
    const currentProduct = waitlistPositionsForPlayer.find(p => p.productId === productId);
    const otherPositions = waitlistPositionsForPlayer.filter(p => p.productId !== productId);

    // Generate styles internally
    const styles = generateAllStyles(['position'], isMobile);

    // Build HTML for waitlist positions display with loading spinner
    let html = `
      <!DOCTYPE html>
      <html>
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        ${styles}
        <style>
          /* Loading Spinner Styles */
          .loading-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(255, 255, 255, 0.95);
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            z-index: 9999;
          }

          .spinner {
            width: 40px;
            height: 40px;
            border: 4px solid #f3f3f3;
            border-top: 4px solid #4CAF50;
            border-radius: 50%;
            animation: spin 1s linear infinite;
          }

          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }

          .loading-text {
            margin-top: 20px;
            font-size: 16px;
            color: #666;
            text-align: center;
          }

          .main-content {
            opacity: 0;
            transition: opacity 0.3s ease-in;
          }

          .main-content.loaded {
            opacity: 1;
          }
        </style>
      </head>
      <body>
        <!-- Loading Overlay -->
        <div id="loadingOverlay" class="loading-overlay">
          <div class="spinner"></div>
          <div class="loading-text">
            <div>Checking your waitlist position...</div>
            <div style="font-size: 14px; margin-top: 10px; color: #999;">This usually takes about 5 seconds</div>
          </div>
        </div>

        <!-- Main Content -->
        <div id="mainContent" class="main-content">
          <div class="container">
            <h1>🎉 You're on the Waitlist!</h1>
    `;

    if (currentProduct) {
      html += `
        <div class="position-card">
          <div class="product-name">${this.escapeHtml(currentProduct.productName)}</div>
          <div class="position-number">#${currentProduct.position}</div>
          <div class="position-label">on the waitlist</div>
        </div>
      `;
    }

    if (otherPositions.length > 0) {
      html += `
        <div class="other-positions">
          <h3>Other Waitlist Positions</h3>
      `;

      for (const pos of otherPositions) {
        html += `
          <div class="other-position-item">
            <span>${this.escapeHtml(pos.productName)}</span>
            <span class="position-badge">#${pos.position}</span>
          </div>
        `;
      }

      html += '</div>';
    }

    html += `
          </div>
        </div>

        <script>
          // Hide loading spinner and show content when page is ready
          document.addEventListener('DOMContentLoaded', function() {
            const loadingOverlay = document.getElementById('loadingOverlay');
            const mainContent = document.getElementById('mainContent');

            // Small delay to ensure smooth transition
            setTimeout(function() {
              if (loadingOverlay) {
                loadingOverlay.style.display = 'none';
              }
              if (mainContent) {
                mainContent.classList.add('loaded');
              }
            }, 100);
          });

          // Fallback: Hide loading after 5 seconds in case something goes wrong
          setTimeout(function() {
            const loadingOverlay = document.getElementById('loadingOverlay');
            const mainContent = document.getElementById('mainContent');

            if (loadingOverlay) {
              loadingOverlay.style.display = 'none';
            }
            if (mainContent) {
              mainContent.classList.add('loaded');
            }
          }, 5000);
        </script>
      </body>
      </html>
    `;

    const output = HtmlService.createHtmlOutput(html);

    // Set appropriate styling - allow iframes for all sources
    output.setTitle('Waitlist Position')
      .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);

    return output;
  }

  /**
   * Render locked product page with interactive buttons
   * @param {string} productId - Product ID
   * @param {string} productName - Product/league name
   * @param {string} source - Source of request
   * @returns {GoogleAppsScript.HTML.HtmlOutput} HTML output
   */
  renderInteractivePage(productId, productName, source) {
    const isMobile = detectMobileFromSource(source);

    // Generate styles for forms with loading spinner
    const formStyles = generateAllStyles(['form'], isMobile);
    const loadingStyles = `
      <style>
        /* Loading Spinner Styles */
        .loading-overlay {
          position: fixed;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          background: rgba(255, 255, 255, 0.95);
          display: flex;
          flex-direction: column;
          justify-content: center;
          align-items: center;
          z-index: 9999;
        }

        .spinner {
          width: 40px;
          height: 40px;
          border: 4px solid #f3f3f3;
          border-top: 4px solid #4CAF50;
          border-radius: 50%;
          animation: spin 1s linear infinite;
        }

        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }

        .loading-text {
          margin-top: 20px;
          font-size: 16px;
          color: #666;
          text-align: center;
        }

        .main-content {
          opacity: 0;
          transition: opacity 0.3s ease-in;
        }

        .main-content.loaded {
          opacity: 1;
        }
      </style>
    `;

    // Use template components following the established architecture
    const template = HtmlService.createTemplateFromFile('baseLayout');

    // Set template data
    template.title = 'Join Waitlist';
    template.heading = 'Join Waitlist';
    template.isMobile = isMobile;
    template.productId = productId;
    template.league = productName;
    template.source = source;

    // Combine styles with loading spinner styles
    template.styles = formStyles + loadingStyles;

    // Build content with loading wrapper
    const interactiveContent = this.buildInteractivePageContent(productId, productName, source);
    template.content = `
      <!-- Loading Overlay -->
      <div id="loadingOverlay" class="loading-overlay">
        <div class="spinner"></div>
        <div class="loading-text">
          <div>Loading waitlist form...</div>
          <div style="font-size: 14px; margin-top: 10px; color: #999;">This usually takes about 5 seconds</div>
        </div>
      </div>

      <!-- Main Content -->
      <div id="mainContent" class="main-content">
        ${interactiveContent}
      </div>

      <script>
        // Hide loading spinner and show content when page is ready
        document.addEventListener('DOMContentLoaded', function() {
          const loadingOverlay = document.getElementById('loadingOverlay');
          const mainContent = document.getElementById('mainContent');

          // Small delay to ensure smooth transition
          setTimeout(function() {
            if (loadingOverlay) {
              loadingOverlay.style.display = 'none';
            }
            if (mainContent) {
              mainContent.classList.add('loaded');
            }
          }, 100);
        });

        // Fallback: Hide loading after 5 seconds in case something goes wrong
        setTimeout(function() {
          const loadingOverlay = document.getElementById('loadingOverlay');
          const mainContent = document.getElementById('mainContent');

          if (loadingOverlay) {
            loadingOverlay.style.display = 'none';
          }
          if (mainContent) {
            mainContent.classList.add('loaded');
          }
        }, 5000);
      </script>
    `;

    // Evaluate template and return
    const output = template.evaluate();
    output.setTitle('Join Waitlist')
      .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);

    return output;
  }

  /**
   * Build content for interactive page using modular components
   */
  buildInteractivePageContent(productId, productName, source) {
    // Load main buttons component
    const mainButtonsTemplate = HtmlService.createTemplateFromFile('mainButtons');
    const mainButtons = mainButtonsTemplate.evaluate().getContent();

    // Load join form component
    const joinFormTemplate = HtmlService.createTemplateFromFile('joinForm');
    joinFormTemplate.productId = productId;
    joinFormTemplate.league = productName;
    joinFormTemplate.source = source;
    const joinForm = joinFormTemplate.evaluate().getContent();

    // Load check form component
    const checkFormTemplate = HtmlService.createTemplateFromFile('checkForm');
    checkFormTemplate.productId = productId;
    checkFormTemplate.source = source;
    const checkForm = checkFormTemplate.evaluate().getContent();

    // Load form interactions script
    const formInteractionsTemplate = HtmlService.createTemplateFromFile('formInteractions');
    const formInteractions = formInteractionsTemplate.evaluate().getContent();

    return `
      <p>This league is currently full, but you can join the waitlist!</p>
      ${mainButtons}
      ${joinForm}
      ${checkForm}
      <script>${formInteractions}</script>
    `;
  }

  /**
   * Render error page with proper styling
   * @param {string} message - Error message to display
   * @param {Error} error - Optional error object for additional context
   * @param {boolean} isMobile - Mobile display flag
   * @returns {GoogleAppsScript.HTML.HtmlOutput} HTML output
   */
  renderErrorPage(message, error = null, isMobile = false) {
    const styles = generateAllStyles(['error'], isMobile);

    const html = `<!DOCTYPE html>
<html>
<head>
  <base target="_top">
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Error</title>
  ${styles}
  <style>
    /* Loading Spinner Styles */
    .loading-overlay {
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(255, 255, 255, 0.95);
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;
      z-index: 9999;
    }

    .spinner {
      width: 40px;
      height: 40px;
      border: 4px solid #f3f3f3;
      border-top: 4px solid #e74c3c;
      border-radius: 50%;
      animation: spin 1s linear infinite;
    }

    @keyframes spin {
      0% { transform: rotate(0deg); }
      100% { transform: rotate(360deg); }
    }

    .loading-text {
      margin-top: 20px;
      font-size: 16px;
      color: #666;
      text-align: center;
    }

    .main-content {
      opacity: 0;
      transition: opacity 0.3s ease-in;
    }

    .main-content.loaded {
      opacity: 1;
    }
  </style>
</head>
<body>
  <!-- Loading Overlay -->
  <div id="loadingOverlay" class="loading-overlay">
    <div class="spinner"></div>
    <div class="loading-text">
      <div>Processing request...</div>
    </div>
  </div>

  <!-- Main Content -->
  <div id="mainContent" class="main-content">
    <div class="container">
      <div class="error-container">
        <div class="error-icon">⚠️</div>
        <h1 class="error-title">Oops! Something went wrong</h1>
        <p class="error-description">${this.escapeHtml(message)}</p>
        ${error?.stack ? `
          <div class="error-details">
            <details>
              <summary>Technical Details</summary>
              <pre>${this.escapeHtml(error.stack)}</pre>
            </details>
          </div>
        ` : ''}
        <div class="back-button">
          <button class="button" onclick="window.history.back()">← Go Back</button>
        </div>
      </div>
    </div>
  </div>

  <script>
    // Hide loading spinner and show content when page is ready
    document.addEventListener('DOMContentLoaded', function() {
      const loadingOverlay = document.getElementById('loadingOverlay');
      const mainContent = document.getElementById('mainContent');

      // Small delay to ensure smooth transition
      setTimeout(function() {
        if (loadingOverlay) {
          loadingOverlay.style.display = 'none';
        }
        if (mainContent) {
          mainContent.classList.add('loaded');
        }
      }, 100);
    });

    // Fallback: Hide loading after 3 seconds for error pages
    setTimeout(function() {
      const loadingOverlay = document.getElementById('loadingOverlay');
      const mainContent = document.getElementById('mainContent');

      if (loadingOverlay) {
        loadingOverlay.style.display = 'none';
      }
      if (mainContent) {
        mainContent.classList.add('loaded');
      }
    }, 3000);
  </script>
</body>
</html>`;

    return HtmlService.createHtmlOutput(html)
      .setTitle('Error')
      .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
  }

  /**
   * Serve locked product page with interactive buttons
   * Only called when user is logged out on Shopify
   * @param {string} productId - Product ID
   * @param {string} league - Product/league name
   * @param {string} source - Source of request
   * @returns {GoogleAppsScript.HTML.HtmlOutput} HTML response
   */
  serveLockedProductPage(productId, league, source) {
    try {
      if (!productId) {
        return this.renderErrorPage('Product ID is required.');
      }

      return this.renderInteractivePage(productId, league, source);

    } catch (error) {
      return this.renderErrorPage(`Error loading product page: ${this.escapeHtml(error.message)}`, error);
    }
  }

  /**
   * Create JSON response for API calls
   * @param {Object} data - Response data
   * @param {number} statusCode - HTTP status code
   * @returns {GoogleAppsScript.Content.TextOutput} JSON response
   */
  renderJsonResponse(data, statusCode = 200) {
    const response = {
      success: statusCode >= 200 && statusCode < 300,
      statusCode,
      data
    };

    return ContentService
      .createTextOutput(JSON.stringify(response))
      .setMimeType(ContentService.MimeType.JSON);
  }

  /**
   * Create error response with optional Slack notification
   * @param {string} context - Error context
   * @param {Error} error - Error object
   * @param {Object} params - Request parameters
   * @param {boolean} notifySlack - Whether to send Slack notification
   * @returns {GoogleAppsScript.Content.TextOutput} JSON error response
   */
  renderErrorResponse(context, error, params = {}, notifySlack = false) {
    if (notifySlack) {
      this.sendSlackErrorNotification(context, error, params);
    }

    return this.renderJsonResponse({
      success: false,
      message: `Error: ${error?.message || 'Unknown error'}`
    }, 500);
  }

  /**
   * Send error notification to Slack
   * TODO: Move this to integrations/SlackClient.js
   * @param {string} context - Error context
   * @param {Error} error - Error object
   * @param {Object} requestData - Request data
   */
  sendSlackErrorNotification(context, error, requestData) {
    const errorMessage = `🚨 *Waitlist Error - ${context}*

*Error:* ${error?.message || 'Unknown error'}

*Request Data:* \`\`\`${JSON.stringify(requestData || {}, null, 2)}\`\`\`

*Stack:* \`\`\`${error?.stack || 'No stack trace available'}\`\`\`

*Source:* waitlist-new-gas
*Time:* ${new Date().toISOString()}`;

    try {
      // TODO: Import and use SlackClient when it's created
      // sendSlackMessage(errorMessage);
      console.error('Slack notification (not implemented):', errorMessage);
    } catch (slackError) {
      console.error('Failed to send Slack notification:', slackError);
    }
  }

  /**
   * Create success response after signup
   * @param {Object} signupResult - Result from signup service
   * @param {string} email - User's email
   * @param {string} customerId - User's customer ID
   * @param {string} productId - Product ID
   * @param {string} source - Source of request
   * @returns {GoogleAppsScript.HTML.HtmlOutput} HTML output
   */
  renderSignupSuccess(signupResult, productId, source) {
    // After successful signup, show positions page
    const positions = [{
      productId,
      productName: signupResult.productName,
      position: signupResult.position
    }];

    return this.renderPositionsPage(positions, productId, source);
  }

  /**
   * Render loading page that immediately shows spinner, then fetches data via JavaScript
   * @param {string} productId - Product ID
   * @param {string} email - User's email (optional)
   * @param {string} customerId - User's customer ID (optional)
   * @param {string} source - Source of request
   * @param {string} league - Product/league name
   * @returns {GoogleAppsScript.HTML.HtmlOutput} HTML output
   */
  renderLoadingPage(productId, email, customerId, source, league) {
    const isMobile = detectMobileFromSource(source);
    const styles = generateAllStyles(['position'], isMobile);

    // Determine loading message based on whether we have user identification
    const hasUserInfo = email || customerId;
    const loadingMessage = hasUserInfo ? 'Checking your waitlist position...' : 'Loading...';

    const html = `
      <!DOCTYPE html>
      <html>
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Waitlist Position</title>
        ${styles}
        <style>
          /* Loading Spinner Styles */
          .loading-container {
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            text-align: center;
            background: #fafafa;
          }

          .spinner {
            width: 50px;
            height: 50px;
            border: 5px solid #f3f3f3;
            border-top: 5px solid #4CAF50;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin-bottom: 20px;
          }

          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }

          .loading-text {
            font-size: 18px;
            color: #333;
            margin-bottom: 10px;
          }

          .loading-subtext {
            font-size: 14px;
            color: #666;
            margin-bottom: 30px;
          }

          .content-container {
            display: none;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
          }

          .content-container.loaded {
            display: block;
          }

          .error-container {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
          }
        </style>
      </head>
      <body>
        <!-- Loading State -->
        <div id="loadingContainer" class="loading-container">
          <div class="spinner"></div>
          <div class="loading-text">${loadingMessage}</div>
          <div class="loading-subtext">This usually takes about 5 seconds</div>
        </div>

        <!-- Content Container (Hidden Initially) -->
        <div id="contentContainer" class="content-container">
          <!-- Content will be populated by JavaScript -->
        </div>

        <script>
          // Configuration
          const CONFIG = {
            productId: '${this.escapeHtml(productId)}',
            email: '${email ? this.escapeHtml(email) : ''}',
            customerId: '${customerId ? this.escapeHtml(customerId) : ''}',
            source: '${this.escapeHtml(source)}',
            league: '${league ? this.escapeHtml(league) : ''}'
          };

          // Fetch position data from server using google.script.run
          function fetchPositionData() {
            try {
              google.script.run
                .withSuccessHandler(function(data) {
                  if (data.success) {
                    if (data.type === 'positions') {
                      renderPositionsContent(data.positions, CONFIG.productId);
                    } else if (data.type === 'locked') {
                      renderLockedContent(CONFIG.productId, CONFIG.league);
                    }
                  } else {
                    renderError(data.message || 'Failed to load position data');
                  }
                })
                .withFailureHandler(function(error) {
                  console.error('Error fetching position data:', error);
                  renderError('Server error. Please refresh the page to try again.');
                })
                .getPositionData(CONFIG.productId, CONFIG.email, CONFIG.customerId);

            } catch (error) {
              console.error('Error calling server function:', error);
              renderError('System error. Please refresh the page to try again.');
            }
          }

          // Render positions content
          function renderPositionsContent(positions, currentProductId) {
            const currentProduct = positions.find(p => p.productId === currentProductId);
            const otherPositions = positions.filter(p => p.productId !== currentProductId);

            let html = '<div class="container"><h1>🎉 You\\'re on the Waitlist!</h1>';

            if (currentProduct) {
              html += \`
                <div class="position-card">
                  <div class="product-name">\${escapeHtml(currentProduct.productName)}</div>
                  <div class="position-number">#\${currentProduct.position}</div>
                  <div class="position-label">on the waitlist</div>
                </div>
              \`;
            }

            if (otherPositions.length > 0) {
              html += '<div class="other-positions"><h3>Other Waitlist Positions</h3>';
              for (const pos of otherPositions) {
                html += \`
                  <div class="other-position-item">
                    <span>\${escapeHtml(pos.productName)}</span>
                    <span class="position-badge">#\${pos.position}</span>
                  </div>
                \`;
              }
              html += '</div>';
            }

            html += '</div>';
            showContent(html);
          }

          // Render locked content (signup form)
          function renderLockedContent(productId, league) {
            const html = \`
              <div class="container">
                <h1>Join the Waitlist</h1>
                <p>This league is currently full, but you can join the waitlist!</p>
                <div style="text-align: center; padding: 40px;">
                  <button onclick="location.reload()" style="
                    background: #4CAF50;
                    color: white;
                    border: none;
                    padding: 12px 24px;
                    border-radius: 6px;
                    font-size: 16px;
                    cursor: pointer;
                  ">Join Waitlist</button>
                </div>
              </div>
            \`;
            showContent(html);
          }

          // Render error content
          function renderError(message) {
            const html = \`
              <div class="error-container">
                <h2>Oops! Something went wrong</h2>
                <p>\${escapeHtml(message)}</p>
                <button onclick="location.reload()" style="
                  background: #e74c3c;
                  color: white;
                  border: none;
                  padding: 10px 20px;
                  border-radius: 4px;
                  margin-top: 15px;
                  cursor: pointer;
                ">Try Again</button>
              </div>
            \`;
            showContent(html);
          }

          // Show content and hide loading
          function showContent(html) {
            const loadingContainer = document.getElementById('loadingContainer');
            const contentContainer = document.getElementById('contentContainer');

            if (contentContainer) {
              contentContainer.innerHTML = html;
              contentContainer.classList.add('loaded');
            }

            if (loadingContainer) {
              loadingContainer.style.display = 'none';
            }
          }

          // HTML escape helper
          function escapeHtml(str) {
            if (!str) return '';
            const div = document.createElement('div');
            div.textContent = str;
            return div.innerHTML;
          }

          // Start fetching data when page loads
          document.addEventListener('DOMContentLoaded', fetchPositionData);
        </script>
      </body>
      </html>
    `;

    const output = HtmlService.createHtmlOutput(html);
    output.setTitle('Waitlist Position')
      .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);

    return output;
  }
}