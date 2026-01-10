#!/usr/bin/env node

/*
🔍 Purpose of debug-proxy-server.js:
This is a debugging tool for troubleshooting Google Apps Script web app issues! Here's what it does:
🎯 Main Function:
Local HTTP Proxy that sits between your browser and a GAS web app to intercept and log all traffic.
🛠️ How It Works:
Runs locally on http://localhost:3001
Forwards requests to the hardcoded GAS web app URL:
exec
Logs everything in detail:
✅ Incoming request details (method, URL, headers, query params)
✅ Outgoing request to GAS
✅ GAS response (status, headers, body, timing)
✅ Response forwarded back to browser
🔧 Usage Scenario:
This was likely created to debug the waitlist web app issues you were having! Instead of clicking the direct GAS link in emails, you would:
Start the proxy: node debug-proxy-server.js
Update email links to use http://localhost:3001/?email=...&league=...
Click the link → see detailed logs of what's happening
Debug the issue by examining request/response data
💡 Benefits:
🔍 Full visibility into GAS web app communication
⏱️ Performance timing (response duration)
📋 Request/response logging for debugging
🚫 Error handling with detailed error pages
📱 Works with email links by replacing the GAS URL with localhost
🎯 Perfect for Debugging:
Web app URL issues (like the ScriptApp.getService().getUrl() problems)
Parameter passing problems
Response format issues
Performance bottlenecks
Authentication/authorization issues
This is a really clever debugging tool for GAS development! 🚀
*/

const http = require('http');
const https = require('https');
const url = require('url');
const querystring = require('querystring');

// Configuration
const LOCAL_PORT = 3001;
const GAS_WEB_APP_URL = 'https://script.google.com/macros/s/AKfycby2GMTxZkXKg19k-su5Mp9hN0smyzdKRXfoXOOOVZ0MCoPFox8oIeEukxpWriPBF7nz/exec';

console.log('🚀 Starting Debug Proxy Server for Google Apps Script...');
console.log(`📡 Local server: http://localhost:${LOCAL_PORT}`);
console.log(`🎯 Target GAS URL: ${GAS_WEB_APP_URL}`);
console.log('');

const server = http.createServer((req, res) => {
  const timestamp = new Date().toISOString();
  const parsedUrl = url.parse(req.url, true);

  console.log('=' .repeat(80));
  console.log(`🔥 [${timestamp}] Incoming Request`);
  console.log('=' .repeat(80));
  console.log(`📝 Method: ${req.method}`);
  console.log(`📝 URL: ${req.url}`);
  console.log(`📝 Path: ${parsedUrl.pathname}`);
  console.log(`📝 Query Params:`, parsedUrl.query);
  console.log(`📝 Headers:`, JSON.stringify(req.headers, null, 2));

  // If this is a favicon request, ignore it
  if (parsedUrl.pathname === '/favicon.ico') {
    res.writeHead(404);
    res.end();
    return;
  }

  // Build the target URL with query parameters
  const targetUrl = GAS_WEB_APP_URL + (req.url.startsWith('?') ? req.url : '?' + querystring.stringify(parsedUrl.query));

  console.log(`🎯 Forwarding to: ${targetUrl}`);
  console.log('');

  // Forward the request to Google Apps Script
  const startTime = Date.now();
  https.get(targetUrl, (gasResponse) => {
    const endTime = Date.now();
    const duration = endTime - startTime;

    console.log('📨 Response from Google Apps Script:');
    console.log(`📝 Status: ${gasResponse.statusCode} ${gasResponse.statusMessage}`);
    console.log(`📝 Headers:`, JSON.stringify(gasResponse.headers, null, 2));
    console.log(`⏱️  Duration: ${duration}ms`);

    let responseBody = '';
    gasResponse.on('data', (chunk) => {
      responseBody += chunk;
    });

    gasResponse.on('end', () => {
      console.log(`📝 Response Body (${responseBody.length} chars):`);
      console.log('-'.repeat(40));
      if (responseBody.length < 2000) {
        console.log(responseBody);
      } else {
        console.log(responseBody.substring(0, 1000) + '\n...[TRUNCATED]...\n' + responseBody.substring(responseBody.length - 500));
      }
      console.log('-'.repeat(40));
      console.log('');

      // Forward the response back to the client
      res.writeHead(gasResponse.statusCode, gasResponse.headers);
      res.end(responseBody);
    });

  }).on('error', (error) => {
    console.log('❌ Error forwarding to Google Apps Script:');
    console.log(error);

    res.writeHead(500, {'Content-Type': 'text/html'});
    res.end(`
      <div style="font-family: Arial, sans-serif; padding: 20px;">
        <h2 style="color: red;">❌ Proxy Error</h2>
        <p>Failed to forward request to Google Apps Script:</p>
        <pre>${error.message}</pre>
        <p><strong>Target URL:</strong> ${targetUrl}</p>
      </div>
    `);
  });
});

server.listen(LOCAL_PORT, () => {
  console.log(`✅ Debug Proxy Server running on http://localhost:${LOCAL_PORT}`);
  console.log('');
  console.log('📋 To test:');
  console.log(`   1. Update your email template to use: http://localhost:${LOCAL_PORT}/?email=...&league=...&timestamp=...`);
  console.log(`   2. Click the link in your email`);
  console.log(`   3. Watch the logs here to see what's being sent and received`);
  console.log('');
  console.log('🛑 Press Ctrl+C to stop the server');
  console.log('');
});

// Graceful shutdown
process.on('SIGINT', () => {
  console.log('\n🛑 Shutting down Debug Proxy Server...');
  server.close(() => {
    console.log('✅ Server closed. Goodbye!');
    process.exit(0);
  });
});
