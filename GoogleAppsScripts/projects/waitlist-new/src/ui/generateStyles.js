/**
 * CSS style generation utilities and JavaScript scripts
 * Pure functions for generating CSS styles and utility scripts
 */

/**
 * Detect mobile device from source or user agent
 */
export function detectMobileFromSource(source) {
  return source === 'shopify';
}

/**
 * Generate base styles for all pages
 */
export function generateBaseStyles(isMobile = false) {
  return `
    <style>
      * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
      }

      body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        line-height: 1.6;
        color: #333;
        background: #f8f9fa;
        ${isMobile ? 'padding: 10px;' : 'padding: 20px;'}
      }

      .container {
        max-width: ${isMobile ? '100%' : '600px'};
        margin: 0 auto;
        background: white;
        padding: ${isMobile ? '15px' : '30px'};
        border-radius: 12px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
      }

      h1, h2, h3 {
        color: #2c3e50;
        margin-bottom: 15px;
      }

      .button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 12px 24px;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.3s ease;
        text-decoration: none;
        display: inline-block;
        margin: 5px;
      }

      .button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102,126,234,0.4);
      }

      .form-group {
        margin-bottom: 20px;
      }

      label {
        display: block;
        margin-bottom: 5px;
        font-weight: 500;
        color: #555;
      }

      input[type="text"], input[type="email"], input[type="tel"] {
        width: 100%;
        padding: 12px;
        border: 2px solid #e0e0e0;
        border-radius: 6px;
        font-size: 16px;
        transition: border-color 0.3s ease;
      }

      input:focus {
        outline: none;
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102,126,234,0.1);
      }

      .error-message {
        color: #e74c3c;
        background: #fdf2f2;
        padding: 12px;
        border-radius: 6px;
        border-left: 4px solid #e74c3c;
        margin: 15px 0;
      }

      .success-message {
        color: #27ae60;
        background: #f1f8ff;
        padding: 12px;
        border-radius: 6px;
        border-left: 4px solid #27ae60;
        margin: 15px 0;
      }
    </style>
  `;
}

/**
 * Generate styles for waitlist position display
 */
export function generatePositionStyles(isMobile = false) {
  return `
    <style>
      .position-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: ${isMobile ? '20px' : '30px'};
        border-radius: 12px;
        text-align: center;
        margin: 20px 0;
        box-shadow: 0 6px 25px rgba(102,126,234,0.3);
      }

      .position-number {
        font-size: ${isMobile ? '3em' : '4em'};
        font-weight: bold;
        margin: 10px 0;
        text-shadow: 0 2px 4px rgba(0,0,0,0.3);
      }

      .position-label {
        font-size: ${isMobile ? '1.1em' : '1.3em'};
        opacity: 0.9;
      }

      .product-name {
        font-size: ${isMobile ? '1.4em' : '1.6em'};
        margin-bottom: 10px;
        font-weight: 600;
      }

      .other-positions {
        margin-top: 30px;
        padding-top: 20px;
        border-top: 2px solid #e0e0e0;
      }

      .other-position-item {
        background: #f8f9fa;
        padding: 15px;
        margin: 10px 0;
        border-radius: 8px;
        border-left: 4px solid #667eea;
        display: flex;
        justify-content: space-between;
        align-items: center;
      }

      .position-badge {
        background: #667eea;
        color: white;
        padding: 5px 12px;
        border-radius: 15px;
        font-weight: 600;
        font-size: 0.9em;
      }
    </style>
  `;
}

/**
 * Generate all styles for a page
 */
export function generateAllStyles(styleTypes = [], isMobile = false) {
  let styles = generateBaseStyles(isMobile);

  if (styleTypes.includes('position')) {
    styles += generatePositionStyles(isMobile);
  }

  return styles;
}